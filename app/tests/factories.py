import hashlib

import factory
from django.conf import settings

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.evaluation.models import Submission, Job, Method, Result
from grandchallenge.pages.models import Page
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.teams.models import Team, TeamMember
from grandchallenge.uploads.models import UploadModel

SUPER_SECURE_TEST_PASSWORD = 'testpasswd'


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f'test_user_{n:04}')
    email = factory.LazyAttribute(lambda u: '%s@test.com' % u.username)
    password = factory.PostGenerationMethodCall(
        'set_password', SUPER_SECURE_TEST_PASSWORD
    )
    is_active = True
    is_staff = False
    is_superuser = False


class ChallengeFactory(factory.DjangoModelFactory):
    class Meta:
        model = Challenge

    short_name = factory.Sequence(lambda n: f'test_challenge_{n}')
    creator = factory.SubFactory(UserFactory)


class ExternalChallengeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ExternalChallenge

    short_name = factory.Sequence(lambda n: f'test_external_challenge{n}')
    homepage = factory.Faker('url')


class PageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Page

    challenge = factory.SubFactory(ChallengeFactory)
    title = factory.Sequence(lambda n: f'page_{n}')
    html = factory.LazyAttribute(lambda t: f'<h2>{t.title}</h2>')


class UploadFactory(factory.DjangoModelFactory):
    class Meta:
        model = UploadModel

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()
    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'file_{n}')


class RegistrationRequestFactory(factory.DjangoModelFactory):
    class Meta:
        model = RegistrationRequest

    user = factory.SubFactory(UserFactory)
    challenge = factory.SubFactory(ChallengeFactory)


def hash_sha256(s):
    m = hashlib.sha256()
    m.update(s.encode())
    return f'sha256:{m.hexdigest()}'


class MethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = Method

    challenge = factory.SubFactory(ChallengeFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f'image{n}'))


class SubmissionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Submission

    challenge = factory.SubFactory(ChallengeFactory)
    file = factory.django.FileField()
    creator = factory.SubFactory(UserFactory)


class JobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job

    challenge = factory.SubFactory(ChallengeFactory)
    method = factory.SubFactory(MethodFactory)
    submission = factory.SubFactory(SubmissionFactory)


class ResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(JobFactory)


class TeamFactory(factory.DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: 'test_team_%s' % n)
    challenge = factory.SubFactory(ChallengeFactory)


class TeamMemberFactory(factory.DjangoModelFactory):
    class Meta:
        model = TeamMember

    team = factory.SubFactory(TeamFactory)
