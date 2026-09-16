"""Run: FORUM_BACKEND=mock ./demo-venv/bin/python -m unittest discover -s demo/tests -v

All rooms live in a temporary database; model calls use local test fixtures.
"""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

TEMP = tempfile.TemporaryDirectory(prefix="forum-tests-")
os.environ["FORUM_DB"] = str(Path(TEMP.name) / "forum.db")
os.environ["FORUM_BACKEND"] = "mock"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from forum import db, service
from forum.engine import Deliberation
from forum.llm import MockBackend
from server import app


class TestMediator:
    name = "local-test-fixture"

    def complete_json(self, task, prompt, context):
        if task == "landscape":
            return {"common_ground": ["Safe and accessible streets"], "cruxes": ["How to preserve deliveries"], "clusters": []}
        if task == "opposing":
            return {"summary": "People want a welcoming street.", "counter": "Some people need car access."}
        if task == "offer":
            quote = "Keep accessible door-to-door access open."
            return {"title": "A practical street trial", "summary": "Test the change for six weeks.",
                    "text": quote + " Review the trial after six weeks.", "rationale": "Balance access and quiet.",
                    "tradeoffs": ["General parking is moved."], "draws_from": [], "addresses": [],
                    "changes": [{"concern_id": c, "status": "addressed", "proposal_quote": quote,
                                 "explanation": "This preserves access."} for c in re.findall(r"concern_id=([a-f0-9]+)", prompt)]}
        if task == "report":
            return {"summary": f"{context['approval']:.0%} accepted after {context['rounds']} rounds.",
                    "agreed": ["Preserve access"], "contested": ["The cost of the trial"], "evolution": "Access was preserved."}
        raise AssertionError(task)


class Journeys(unittest.TestCase):
    def setUp(self):
        service._backend = MockBackend()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def post(self, path, body=None, client=None, expected=200):
        response = (client or self.client).post(path, json=body or {})
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def state(self, room, client=None):
        response = (client or self.client).get('/api/d/' + room)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def wait(self, room, status, rounds=None):
        until = time.monotonic() + 5
        while time.monotonic() < until:
            s = self.state(room)
            if s['status'] == status and not s['busy'] and (rounds is None or len(s['rounds']) == rounds):
                return s
            time.sleep(.02)
        self.fail(f"Expected {status}, got {s}")

    def respond(self, room, response, client=None, objection="Please preserve access.", state=None, expected=200):
        s = state or self.state(room, client)
        r = s['rounds'][-1]
        return self.post(f'/api/d/{room}/respond', {'response': response, 'objection': objection,
                         'round_number': r['number'], 'proposal_id': r['offer']['id']}, client, expected)

    def example(self, choice='deliveries'):
        room = self.post('/api/examples')['id']
        self.post(f'/api/d/{room}/position', {'choice': choice})
        return room

    def live(self, count=3):
        service._backend = TestMediator()
        clients = [self.client] + [TestClient(app) for _ in range(count - 1)]
        room = self.post('/api/deliberations', {'topic': 'Should Market Street be car-free on Saturdays?'})['id']
        for i, client in enumerate(clients):
            self.post(f'/api/d/{room}/position', {'text': f'View {i}: keep the street accessible.'}, client)
        self.post(f'/api/d/{room}/begin')
        self.wait(room, 'offered')
        for client in clients:
            self.post(f'/api/d/{room}/continue', client=client)
        return room, clients

    def test_example_branches_and_report_counts(self):
        for choice in ('deliveries', 'access', 'parking'):
            for first in ('accept', 'object'):
                for last in ('accept', 'object'):
                    with self.subTest(choice=choice, first=first, last=last):
                        room = self.example(choice)
                        self.assertEqual(self.state(room)['status'], 'landscape')
                        self.post(f'/api/d/{room}/continue')
                        self.respond(room, first)
                        s = self.state(room)
                        self.assertEqual(s['status'], 'evaluated')
                        self.assertEqual(s['rounds'][0]['accepting'], 2 + (first == 'accept'))
                        self.post(f'/api/d/{room}/continue')
                        s = self.state(room)
                        concerns = s['me']['concerns']
                        self.assertEqual(len(concerns), int(first == 'object'))
                        if concerns:
                            a = concerns[0]['assessment']
                            self.assertIn(a['proposal_quote'], s['rounds'][-1]['offer']['text'])
                            self.assertEqual(a['status'], 'not_addressed' if choice == 'parking' else 'addressed')
                        self.respond(room, last)
                        s = self.state(room)
                        expected = 'consensus' if last == 'accept' else 'dissensus'
                        self.assertEqual(s['status'], expected)
                        self.assertEqual(s['rounds'][-1]['accepting'], 3 + (last == 'accept'))
                        self.assertIn(f"{3 + (last == 'accept')} of 5", s['report']['summary'])
                        self.assertIn('parking', ' '.join(s['report']['contested']))
                        self.assertEqual(s['process']['calls'], 0)

    def test_example_observer_cannot_modify(self):
        room = self.post('/api/examples')['id']
        stranger = TestClient(app)
        self.post(f'/api/d/{room}/position', {'choice': 'access'}, stranger, 403)
        self.assertEqual(self.state(room)['status'], 'gathering')
        self.post(f'/api/d/{room}/position', {'choice': 'arbitrary'}, expected=409)

    def test_perspective_gate_and_stale_response(self):
        room = self.example()
        self.post(f'/api/d/{room}/continue')
        first = self.state(room)
        self.respond(room, 'object')
        self.respond(room, 'object', state=first, expected=409)
        self.post(f'/api/d/{room}/continue')
        self.respond(room, 'accept', state=first, expected=409)
        self.assertFalse(self.state(room)['me']['responded'])
        self.post(f'/api/d/{room}/continue')  # Duplicate navigation cannot make version 3.
        self.assertEqual(len(self.state(room)['rounds']), 2)

    def test_mock_cannot_create_arbitrary_live_topic(self):
        self.post('/api/deliberations', {'topic': 'Should we change the park opening hours?'}, expected=409)
        self.assertFalse(self.client.get('/api/me').json()['live_available'])

    def test_live_room_stays_readable_and_pauses_without_its_mediator(self):
        room, _ = self.live()
        original = self.state(room)['rounds']
        service._backend = MockBackend()
        service.advance(room)
        saved = self.state(room)
        self.assertTrue(saved['error'])
        self.assertEqual(saved['rounds'], original)
        with patch.object(service, 'backend', side_effect=RuntimeError('Missing provider setup')):
            self.assertEqual(self.state(room)['speaker_count'], 3)
            self.assertEqual(self.client.get('/api/me/feed').status_code, 200)
        service._backend = TestMediator()
        self.post(f'/api/d/{room}/retry')
        self.assertIsNone(self.state(room)['error'])

    def test_identity_and_private_profile(self):
        room = self.example()
        user = self.client.get('/api/me').json()['user']
        other = TestClient(app)
        self.post('/api/login', {'handle': user['handle']}, other, 410)
        self.assertIsNone(other.get('/api/me').json()['user'])
        self.assertEqual(other.get('/api/users/' + user['handle']).status_code, 403)
        self.post('/api/me/name', {'handle': 'participant-' + room})
        self.assertEqual(self.client.get('/api/me').json()['user']['id'], user['id'])
        self.assertTrue(self.state(room)['me']['has_position'])
        mine = next(o for o in self.state(room)['opinions'] if o['id'] == user['id'])
        self.assertEqual(mine['name'], 'participant-' + room)

    def test_return_feed_and_observer_result(self):
        room = self.example()
        feed = self.client.get('/api/me/feed').json()
        self.assertIn(room, [r['id'] for r in feed['needs_you']])
        self.post(f'/api/d/{room}/continue')
        self.respond(room, 'object')
        self.post(f'/api/d/{room}/continue')
        self.respond(room, 'accept')
        feed = self.client.get('/api/me/feed').json()
        self.assertIn(room, [r['id'] for r in feed['outcomes']])
        observer = self.state(room, TestClient(app))
        self.assertIsNone(observer['me'])
        self.assertEqual(observer['rounds'][-1]['accepting'], 4)
        self.assertNotIn('responses', observer['rounds'][-1])
        self.assertNotIn('changes', observer['rounds'][-1]['offer'])
        self.assertNotIn(room, [r['id'] for r in self.client.get('/api/deliberations').json()['deliberations']])

    def test_group_waits_for_intake_then_revises(self):
        service._backend = TestMediator()
        room = self.post('/api/deliberations', {'topic': 'Should our street have a six-week trial?'})['id']
        self.post(f'/api/d/{room}/position', {'text': 'Keep access open.'})
        self.assertEqual(self.state(room)['status'], 'gathering')
        self.post(f'/api/d/{room}/begin', expected=409)
        clients = [self.client, TestClient(app), TestClient(app)]
        for client in clients[1:]:
            self.post(f'/api/d/{room}/position', {'text': 'Please consider local shops.'}, client)
        self.assertEqual(self.state(room)['status'], 'gathering')
        self.post(f'/api/d/{room}/begin')
        self.wait(room, 'offered')
        self.respond(room, 'accept', expected=409)  # Must see perspective first.
        for client in clients:
            self.post(f'/api/d/{room}/continue', client=client)
        self.respond(room, 'object', objection='PRIVATE: retain door-to-door access.')
        waiting = self.state(room)
        self.assertTrue(waiting['me']['responded'])
        self.assertIn('text', waiting['rounds'][-1]['offer'])
        self.assertNotIn('approval', waiting['rounds'][-1])
        for client in clients[1:]:
            self.respond(room, 'accept', client)
        s = self.wait(room, 'offered', 2)
        self.assertEqual(s['me']['concerns'][0]['assessment']['status'], 'addressed')
        outsider = TestClient(app)
        public = self.state(room, outsider)
        self.assertNotIn('PRIVATE:', json.dumps(public))
        audit = outsider.get(f'/api/d/{room}/audit').json()
        self.assertNotIn('prompt', json.dumps(audit))
        self.assertNotIn('PRIVATE:', json.dumps(audit))
        self.post(f'/api/d/{room}/position', {'text': 'Late view'}, outsider, 409)
        for client in clients:
            self.respond(room, 'accept', client)
        final = self.wait(room, 'consensus')
        self.assertEqual(final['rounds'][-1]['accepting'], 3)
        self.assertEqual(final['rounds'][-1]['eligible'], 3)

    def test_deadline_runs_without_room_reads_and_absence_is_not_consent(self):
        room, clients = self.live(3)
        self.respond(room, 'accept')
        with service._lock(room):
            d, staged, config = service._load(room)
            staged['closes_at'] = time.time() - 1
            service._save(room, d, staged)
        # Only read SQLite here: no API view or manual advancement triggers closure.
        until = time.monotonic() + 4
        while time.monotonic() < until:
            row = db.load_deliberation(room)
            if row['status'] == 'insufficient':
                break
            time.sleep(.04)
        self.assertEqual(row['status'], 'insufficient')
        self.assertAlmostEqual(row['state']['rounds'][0]['approval'], 1/3)
        self.assertEqual(len(row['state']['rounds']), 1)

    def test_expired_intake_without_quorum(self):
        service._backend = TestMediator()
        room = self.post('/api/deliberations', {'topic': 'Should we try a quieter Saturday?'})['id']
        self.post(f'/api/d/{room}/position', {'text': 'I support a trial.'})
        row = db.load_deliberation(room)
        row['config']['intake_closes_at'] = time.time() - 1
        db.conn().execute('UPDATE deliberations SET config=? WHERE id=?', (json.dumps(row['config']), room))
        db.conn().commit()
        self.post(f'/api/d/{room}/position', {'text': 'Too late'}, TestClient(app), 409)
        service.tick()
        self.assertEqual(self.state(room)['status'], 'insufficient')

    def test_state_serialization_preserves_journey(self):
        room = self.example('access')
        self.post(f'/api/d/{room}/continue')
        self.respond(room, 'object')
        row = db.load_deliberation(room)
        d = Deliberation.from_dict(row['state'], backend=service.example.ExampleBackend())
        self.assertEqual(d.status, 'evaluated')
        self.assertEqual(d.scenario['choice'], 'access')
        self.assertEqual(len(d.concerns), 1)
        self.assertEqual(d.rounds[0]['offer']['id'], row['state']['rounds'][0]['offer']['id'])

    def test_mediator_receives_context_and_only_supported_concern_evidence_survives(self):
        d = Deliberation('Should we try car-free Saturdays?', backend=TestMediator(), include_personas=False)
        d.context = 'The trial must preserve all-day disability access.'
        for uid in ('one', 'two', 'three'):
            d.add_position(uid, uid, 'Preserve access.')
        d.begin()
        self.assertTrue(all(d.context in call['prompt'] for call in d.audit))
        d.make_offer()
        d.respond_with({uid: {'response': 'object', 'objection': 'Keep access open.'} for uid in d.humans})
        valid = {'concern_id': d.concerns[0]['id'], 'status': 'addressed',
                 'proposal_quote': 'Access stays open.', 'explanation': 'This preserves access.'}
        offer = {'title': 'An accessible trial', 'text': 'Access stays open.', 'changes': [
            valid, {**valid, 'proposal_quote': 'A clause that is not in the proposal.'},
            {**valid, 'concern_id': 'unknown'}, {**valid, 'status': 'resolved'}]}
        with patch.object(d.backend, 'complete_json', return_value=offer):
            d.make_offer()
        self.assertEqual(d.rounds[-1]['offer']['changes'], [valid])

    def test_scheduler_resumes_persisted_deadline_after_lifespan_restart(self):
        room, clients = self.live(3)
        self.respond(room, 'accept')
        self.client.__exit__(None, None, None)
        with service._lock(room):
            d, staged, config = service._load(room)
            staged['closes_at'] = time.time() - 1
            service._save(room, d, staged)
        self.client.__enter__()
        until = time.monotonic() + 4
        while time.monotonic() < until:
            row = db.load_deliberation(room)
            if row['status'] == 'insufficient':
                break
            time.sleep(.04)
        self.assertEqual(row['status'], 'insufficient')
        self.assertEqual(len(row['state']['rounds'][0]['responses']), 1)

    def test_mediation_failure_preserves_views_and_host_can_retry(self):
        class FailsOnce(TestMediator):
            failed = False

            def complete_json(self, task, prompt, context):
                if task == 'offer' and not self.failed:
                    self.failed = True
                    raise RuntimeError('Test failure, no network call')
                return super().complete_json(task, prompt, context)

        service._backend = FailsOnce()
        room = self.post('/api/deliberations', {'topic': 'Should Market Street try a quiet Saturday?'})['id']
        clients = [self.client, TestClient(app), TestClient(app)]
        for client in clients:
            self.post(f'/api/d/{room}/position', {'text': 'Keep the street accessible.'}, client)
        with self.assertLogs('forum.service', level='ERROR'):
            self.post(f'/api/d/{room}/begin')
            until = time.monotonic() + 4
            while time.monotonic() < until:
                s = self.state(room)
                if s['error'] and not s['busy']:
                    break
                time.sleep(.02)
        self.assertTrue(s['error'])
        self.assertEqual(s['speaker_count'], 3)
        self.assertNotIn('RuntimeError', s['error'])
        self.post(f'/api/d/{room}/retry', client=clients[1], expected=403)
        self.post(f'/api/d/{room}/retry')
        resumed = self.wait(room, 'offered')
        self.assertIsNone(resumed['error'])
        self.assertEqual(len(resumed['rounds']), 1)

    def test_missing_room_is_404_and_input_is_bounded(self):
        self.assertEqual(self.client.get('/api/d/not-a-room').status_code, 404)
        self.post('/api/deliberations', {'topic': 'x' * 241}, expected=422)
        room = self.post('/api/examples')['id']
        self.post(f'/api/d/{room}/position', {'text': 'x' * 5001}, expected=422)


if __name__ == '__main__':
    unittest.main()
