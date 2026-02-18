from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import Http404, JsonResponse
from django.test import RequestFactory, TestCase
from django.views.generic import CreateView as _CreateView
from rest_framework.exceptions import AuthenticationFailed

from qux.token.forms import CustomTokenForm
from qux.token.mixins import TokenAccessMixin, authenticate_user
from qux.token.models import CustomToken, CustomTokenAuthentication
from qux.token.views import (
    CustomTokenCreateView,
    CustomTokenDeleteView,
    CustomTokenDetailView,
    CustomTokenListView,
    CustomTokenUpdateView,
)

User = get_user_model()


class TestCustomTokenStr(TestCase):
    def test_str_returns_name_and_user(self):
        user = User.objects.create_user("tokenuser", password="pass")
        token = CustomToken.objects.create(name="My Token", user=user)
        self.assertEqual(str(token), f"My Token ({user})")


class TestCustomTokenSave(TestCase):
    def test_auto_generates_key_if_not_set(self):
        user = User.objects.create_user("autogen", password="pass")
        token = CustomToken(name="Auto Key", user=user)
        self.assertEqual(token.key, "")
        token.save()
        self.assertTrue(len(token.key) == 40)

    def test_preserves_existing_key(self):
        user = User.objects.create_user("keepkey", password="pass")
        token = CustomToken(name="Preset Key", user=user, key="a" * 40)
        token.save()
        self.assertEqual(token.key, "a" * 40)


class TestCustomTokenGenerateKey(TestCase):
    def test_returns_40_char_hex_string(self):
        key = CustomToken.generate_key()
        self.assertEqual(len(key), 40)
        # Verify it is valid hex
        int(key, 16)


class TestCustomTokenAuthentication(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("authuser", password="pass")
        self.active_token = CustomToken.objects.create(
            name="Active", user=self.user, is_active=True
        )
        self.inactive_token = CustomToken.objects.create(
            name="Inactive", user=self.user, is_active=False
        )

    def test_active_token_succeeds(self):
        auth = CustomTokenAuthentication()
        user, token = auth.authenticate_credentials(self.active_token.key)
        self.assertEqual(user, self.user)
        self.assertEqual(token, self.active_token)

    def test_inactive_token_raises_authentication_failed(self):
        auth = CustomTokenAuthentication()
        with self.assertRaises(AuthenticationFailed) as ctx:
            auth.authenticate_credentials(self.inactive_token.key)
        self.assertIn("deactivated", str(ctx.exception.detail))


class TestAuthenticateUser(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("mixinuser", password="pass")
        self.token = CustomToken.objects.create(
            name="MixinToken", user=self.user, is_active=True
        )

    def test_valid_token_returns_user(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Token {self.token.key}")
        user = authenticate_user(request)
        self.assertEqual(user, self.user)

    def test_no_token_falls_back_to_request_user(self):
        request = self.factory.get("/")
        anonymous = MagicMock()
        anonymous.is_authenticated = False
        request.user = anonymous
        user = authenticate_user(request)
        self.assertEqual(user, anonymous)


class TestTokenAccessMixinUnauthenticated(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("qux.token.mixins.authenticate_user")
    def test_unauthenticated_user_returns_401(self, mock_auth):
        anonymous = MagicMock()
        anonymous.is_authenticated = False
        mock_auth.return_value = anonymous

        class TestView(TokenAccessMixin):  # pylint: disable=too-few-public-methods
            pass

        request = self.factory.get("/")
        view = TestView()
        response = view.dispatch(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)


class TestTokenAccessMixinNoAccessRequired(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("qux.token.mixins.authenticate_user")
    def test_access_required_none_passes_through(self, mock_auth):
        user = MagicMock()
        user.is_authenticated = True
        mock_auth.return_value = user

        class ParentView:  # pylint: disable=too-few-public-methods
            def dispatch(self, request, *args, **kwargs):
                return JsonResponse(data="OK", safe=False, status=200)

        class TestView(
            TokenAccessMixin, ParentView
        ):  # pylint: disable=too-few-public-methods
            access_required = None

        request = self.factory.get("/")
        view = TestView()
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 200)


class TestTokenAccessMixinWithGroups(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("groupuser", password="pass")
        self.group = Group.objects.create(name="editors")
        self.user.groups.add(self.group)

    @patch("qux.token.mixins.authenticate_user")
    def test_user_in_required_group_passes(self, mock_auth):
        mock_auth.return_value = self.user

        class ParentView:  # pylint: disable=too-few-public-methods
            def dispatch(self, request, *args, **kwargs):
                return JsonResponse(data="OK", safe=False, status=200)

        class TestView(
            TokenAccessMixin, ParentView
        ):  # pylint: disable=too-few-public-methods
            access_required = ["editors"]

        request = self.factory.get("/")
        view = TestView()
        response = view.dispatch(request)
        self.assertEqual(response.status_code, 200)

    @patch("qux.token.mixins.authenticate_user")
    def test_user_not_in_required_group_returns_403(self, mock_auth):
        mock_auth.return_value = self.user

        class ParentView:  # pylint: disable=too-few-public-methods
            def dispatch(self, request, *args, **kwargs):
                return JsonResponse(data="OK", safe=False, status=200)

        class TestView(
            TokenAccessMixin, ParentView
        ):  # pylint: disable=too-few-public-methods
            access_required = ["admins"]

        request = self.factory.get("/")
        view = TestView()
        response = view.dispatch(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)


class TestCustomTokenForm(TestCase):
    def test_save_with_user_creates_token(self):
        user = User.objects.create_user("formuser", password="pass")
        form = CustomTokenForm(data={"name": "Form Token"})
        self.assertTrue(form.is_valid(), form.errors)
        token = form.save(user=user)
        self.assertEqual(token.user, user)
        self.assertEqual(token.name, "Form Token")
        self.assertTrue(len(token.key) == 40)
        self.assertTrue(CustomToken.objects.filter(pk=token.pk).exists())


# ===================================================================
# Token views tests — cover lines in token/views.py
# ===================================================================


class TestCustomTokenListViewGetQueryset(TestCase):
    """Cover lines 32-35: get_queryset filters by request.user."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("listuser", password="pass")
        self.other_user = User.objects.create_user("otheruser", password="pass")
        self.token1 = CustomToken.objects.create(name="Token1", user=self.user)
        self.token2 = CustomToken.objects.create(name="Token2", user=self.other_user)

    def test_get_queryset_filters_by_user(self):
        request = self.factory.get("/")
        request.user = self.user
        view = CustomTokenListView()
        view.request = request
        view.kwargs = {}
        qs = view.get_queryset()
        self.assertIn(self.token1, qs)
        self.assertNotIn(self.token2, qs)


class TestCustomTokenDetailViewGetObject(TestCase):
    """Cover lines 47-56: get_object looks up by user and key."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("detailuser", password="pass")
        self.token = CustomToken.objects.create(name="DetailToken", user=self.user)

    def test_get_object_found(self):
        request = self.factory.get("/")
        request.user = self.user
        view = CustomTokenDetailView()
        view.request = request
        view.kwargs = {"key": self.token.key}
        obj = view.get_object()
        self.assertEqual(obj, self.token)

    def test_get_object_not_found_raises_404(self):
        request = self.factory.get("/")
        request.user = self.user
        view = CustomTokenDetailView()
        view.request = request
        view.kwargs = {"key": "nonexistent"}
        with self.assertRaises(Http404):
            view.get_object()

    def test_get_object_no_key_raises_404(self):
        request = self.factory.get("/")
        request.user = self.user
        view = CustomTokenDetailView()
        view.request = request
        view.kwargs = {}
        with self.assertRaises(Http404):
            view.get_object()


class TestCustomTokenCreateViewFormValid(TestCase):
    """Cover lines 73-75: form_valid calls form.save(user)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("createuser", password="pass")

    def test_form_valid_calls_save_with_user(self):
        form = CustomTokenForm(data={"name": "New Token"})
        self.assertTrue(form.is_valid())

        request = self.factory.post("/")
        request.user = self.user

        view = CustomTokenCreateView()
        view.request = request
        view.kwargs = {}
        view.object = None

        # Mock form.save to verify it's called with user, and mock super
        mock_form = MagicMock()
        with patch.object(
            _CreateView,
            "form_valid",
            return_value=MagicMock(status_code=302),
        ):
            view.form_valid(mock_form)

        # form.save is called with request.user (lines 73-75)
        mock_form.save.assert_called_once_with(self.user)


class TestCustomTokenCreateViewGetSuccessURL(TestCase):
    """Cover lines 77-79: get_success_url returns reverse of token detail."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("successurl", password="pass")

    def test_get_success_url(self):
        token = CustomToken.objects.create(name="SuccessToken", user=self.user)

        view = CustomTokenCreateView()
        view.object = token
        url = view.get_success_url()
        self.assertIn(token.key, url)


class TestCustomTokenUpdateViewGetSuccessURL(TestCase):
    """Cover line 94: static get_success_url returns reverse of home."""

    def test_get_success_url(self):
        url = CustomTokenUpdateView.get_success_url()
        self.assertIn("account/tokens", url)


class TestCustomTokenDeleteViewGetSuccessURL(TestCase):
    """Cover line 103: static get_success_url returns reverse of home."""

    def test_get_success_url(self):
        url = CustomTokenDeleteView.get_success_url()
        self.assertIn("account/tokens", url)
