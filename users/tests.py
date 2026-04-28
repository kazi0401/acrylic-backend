from django.test import TestCase

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import ArtistProfile, ClientProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = '/api/users/register/'
LOGIN_URL = '/api/users/login/'


def make_user(username='testuser', password='testpass123', role=User.Role.CLIENT, **kwargs):
    return User.objects.create_user(username=username, password=password, role=role, **kwargs)


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):

    def test_str_includes_username_and_role(self):
        user = make_user(username='alice', role=User.Role.ARTIST)
        self.assertEqual(str(user), 'alice (artist)')

    def test_default_role_is_client(self):
        user = User.objects.create_user(username='bob', password='pass')
        self.assertEqual(user.role, User.Role.CLIENT)

    def test_role_choices_are_valid(self):
        valid_roles = [User.Role.CLIENT, User.Role.ARTIST, User.Role.ADMIN]
        for role in valid_roles:
            user = User.objects.create_user(
                username=f'user_{role}', password='pass', role=role
            )
            self.assertEqual(user.role, role)


# ---------------------------------------------------------------------------
# Signal tests — profile auto-creation
# ---------------------------------------------------------------------------

class UserProfileSignalTest(TestCase):

    def test_artist_registration_creates_artist_profile(self):
        user = make_user(username='artist1', role=User.Role.ARTIST)
        self.assertTrue(ArtistProfile.objects.filter(user=user).exists())

    def test_client_registration_creates_client_profile(self):
        user = make_user(username='client1', role=User.Role.CLIENT)
        self.assertTrue(ClientProfile.objects.filter(user=user).exists())

    def test_artist_does_not_get_client_profile(self):
        user = make_user(username='artist2', role=User.Role.ARTIST)
        self.assertFalse(ClientProfile.objects.filter(user=user).exists())

    def test_client_does_not_get_artist_profile(self):
        user = make_user(username='client2', role=User.Role.CLIENT)
        self.assertFalse(ArtistProfile.objects.filter(user=user).exists())

    def test_admin_gets_no_profile(self):
        user = make_user(username='admin1', role=User.Role.ADMIN)
        self.assertFalse(ArtistProfile.objects.filter(user=user).exists())
        self.assertFalse(ClientProfile.objects.filter(user=user).exists())

    def test_profile_not_duplicated_on_save(self):
        user = make_user(username='artist3', role=User.Role.ARTIST)
        user.email = 'updated@example.com'
        user.save()  # subsequent save should not create a second profile
        self.assertEqual(ArtistProfile.objects.filter(user=user).count(), 1)

    def test_artist_profile_str(self):
        user = make_user(username='artist4', role=User.Role.ARTIST)
        profile = ArtistProfile.objects.get(user=user)
        self.assertEqual(str(profile), 'ArtistProfile(artist4)')

    def test_client_profile_str(self):
        user = make_user(username='client3', role=User.Role.CLIENT)
        profile = ClientProfile.objects.get(user=user)
        self.assertEqual(str(profile), 'ClientProfile(client3)')

    def test_deleting_user_cascades_to_profile(self):
        user = make_user(username='artist5', role=User.Role.ARTIST)
        user_id = user.pk
        user.delete()
        self.assertFalse(ArtistProfile.objects.filter(user_id=user_id).exists())


# ---------------------------------------------------------------------------
# Register view tests  —  POST /api/users/register/
# ---------------------------------------------------------------------------

class RegisterViewTest(APITestCase):

    # --- Successful registration ---

    def test_register_client_returns_201(self):
        response = self.client.post(REGISTER_URL, {
            'username': 'newclient',
            'email': 'client@example.com',
            'password': 'securepass123',
            'role': 'client',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Account created successfully')

    def test_register_artist_returns_201(self):
        response = self.client.post(REGISTER_URL, {
            'username': 'newartist',
            'email': 'artist@example.com',
            'password': 'securepass123',
            'role': 'artist',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_creates_user_in_db(self):
        self.client.post(REGISTER_URL, {
            'username': 'newclient',
            'email': 'client@example.com',
            'password': 'securepass123',
            'role': 'client',
        })
        self.assertTrue(User.objects.filter(username='newclient').exists())

    def test_register_default_role_is_client(self):
        self.client.post(REGISTER_URL, {
            'username': 'noroleuser',
            'email': 'norole@example.com',
            'password': 'securepass123',
            # role omitted
        })
        user = User.objects.get(username='noroleuser')
        self.assertEqual(user.role, User.Role.CLIENT)

    def test_register_does_not_return_password(self):
        response = self.client.post(REGISTER_URL, {
            'username': 'newclient',
            'email': 'client@example.com',
            'password': 'securepass123',
        })
        self.assertNotIn('password', response.data)

    def test_register_artist_auto_creates_profile(self):
        self.client.post(REGISTER_URL, {
            'username': 'newartist',
            'email': 'artist@example.com',
            'password': 'securepass123',
            'role': 'artist',
        })
        user = User.objects.get(username='newartist')
        self.assertTrue(ArtistProfile.objects.filter(user=user).exists())

    # --- Validation failures ---

    def test_duplicate_username_returns_400(self):
        make_user(username='taken')
        response = self.client.post(REGISTER_URL, {
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_missing_username_returns_400(self):
        response = self.client.post(REGISTER_URL, {
            'email': 'nousername@example.com',
            'password': 'securepass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_missing_password_returns_400(self):
        response = self.client.post(REGISTER_URL, {
            'username': 'nopassword',
            'email': 'nopassword@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_invalid_role_returns_400(self):
        response = self.client.post(REGISTER_URL, {
            'username': 'badrole',
            'email': 'badrole@example.com',
            'password': 'securepass123',
            'role': 'superadmin',  # not a valid choice
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)


# ---------------------------------------------------------------------------
# Login view tests  —  POST /api/users/login/
# ---------------------------------------------------------------------------

class LoginViewTest(APITestCase):

    def setUp(self):
        self.artist = make_user(username='loginartist', role=User.Role.ARTIST)
        self.client_user = make_user(username='loginclient', role=User.Role.CLIENT)

    # --- Successful login ---

    def test_valid_login_returns_200(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginartist',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_returns_access_token(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginartist',
            'password': 'testpass123',
        })
        self.assertIn('access', response.data)

    def test_login_returns_refresh_token(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginartist',
            'password': 'testpass123',
        })
        self.assertIn('refresh', response.data)

    def test_login_returns_correct_role(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginartist',
            'password': 'testpass123',
        })
        self.assertEqual(response.data['role'], 'artist')

    def test_login_returns_client_role_for_client(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginclient',
            'password': 'testpass123',
        })
        self.assertEqual(response.data['role'], 'client')

    # --- Failures ---

    def test_wrong_password_returns_401(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'loginartist',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_nonexistent_user_returns_401(self):
        response = self.client.post(LOGIN_URL, {
            'username': 'doesnotexist',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_credentials_returns_401(self):
        response = self.client.post(LOGIN_URL, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)