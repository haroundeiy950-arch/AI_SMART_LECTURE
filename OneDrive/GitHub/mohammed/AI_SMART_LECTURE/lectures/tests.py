from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Lecture, LiveSession


class LectureSecurityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='test-password-123')
        self.other = User.objects.create_user('other', password='test-password-123')
        self.lecture = Lecture.objects.create(owner=self.owner, title='Networks')

    def test_private_lecture_requires_owner(self):
        self.client.login(username='other', password='test-password-123')
        self.assertEqual(self.client.get(self.lecture.get_absolute_url()).status_code, 404)

    def test_private_share_link_is_hidden(self):
        url = reverse('shared_lecture', args=[self.lecture.share_token])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_shared_link_works(self):
        self.lecture.privacy = 'shared'; self.lecture.save()
        url = reverse('shared_lecture', args=[self.lecture.share_token])
        self.assertContains(self.client.get(url), 'Networks')

    def test_student_can_join_live_by_code(self):
        session = LiveSession.objects.create(lecture=self.lecture)
        self.client.login(username='other', password='test-password-123')
        response = self.client.post(reverse('join_live'), {'code': session.code})
        self.assertRedirects(response, reverse('live_room', args=[session.code]))
        self.assertTrue(session.participants.filter(user=self.other).exists())

    def test_student_can_join_without_code_dash(self):
        session = LiveSession.objects.create(lecture=self.lecture)
        self.client.login(username='other', password='test-password-123')
        code_without_dash = session.code.replace('-', '').lower()
        response = self.client.post(reverse('join_live'), {'code': code_without_dash})
        self.assertRedirects(response, reverse('live_room', args=[session.code]))

    def test_invalid_code_renders_message_instead_of_404(self):
        self.client.login(username='other', password='test-password-123')
        response = self.client.post(reverse('join_live'), {'code': 'HOR35'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrect')

    def test_student_cannot_overwrite_live_board(self):
        session = LiveSession.objects.create(lecture=self.lecture)
        self.client.login(username='other', password='test-password-123')
        session.participants.create(user=self.other)
        self.client.post(reverse('live_api', args=[session.code]),
            data='{"action":"board","image":"data:image/png;base64,bad"}', content_type='application/json')
        session.refresh_from_db()
        self.assertEqual(session.whiteboard_state, '')

# Create your tests here.
