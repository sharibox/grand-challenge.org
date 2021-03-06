import json
import os

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from grandchallenge.evaluation.models import Submission
from tests.factories import UserFactory, ChallengeFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_input, expected",
    [
        ("result", "Result List"),
        ("submission", "Submission List"),
        ("job", "Job List"),
        ("method", "Method List"),
    ],
)
def test_api_pages(client, test_input, expected):
    # Check for the correct HTML view
    url = reverse(f'api:{test_input}-list')
    response = client.get(url, HTTP_ACCEPT='text/html')
    assert expected in force_text(response.content)
    assert response.status_code == 200
    # There should be no content, but we should be able to do json.loads
    response = client.get(url, HTTP_ACCEPT='application/json')
    assert response.status_code == 200
    assert not json.loads(response.content)


@pytest.mark.django_db
def test_token_generation(client):
    token_url = reverse('api:obtain-auth-token')
    # Check that we cannot get a token
    response = client.get(token_url)
    assert response.status_code == 405
    # Check that we can get the token for a new user, using post
    user = UserFactory()
    response = client.post(
        token_url, {'username': user.username, 'password': 'testpasswd'}
    )
    assert response.data['token'] == Token.objects.get(
        user__username=user.username
    ).key
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_file, expected_response",
    [("compressed.zip", 201), ("compressed.7z", 400)],
)
def test_upload_file(client, test_file, expected_response):
    submission_file = os.path.join(
        os.path.split(__file__)[0], 'resources', test_file
    )
    # Get the users token
    user = UserFactory()
    challenge = ChallengeFactory()
    token_url = reverse('api:obtain-auth-token')
    response = client.post(
        token_url, {'username': user.username, 'password': 'testpasswd'}
    )
    token = response.data['token']
    submission_url = reverse('api:submission-list')
    # Upload with token authorisation
    with open(submission_file, 'rb') as f:
        response = client.post(
            submission_url,
            {'file': f, 'challenge': challenge.short_name},
            format='multipart',
            HTTP_AUTHORIZATION='Token ' + token,
        )
    assert response.status_code == expected_response
    # Upload with session authorisation
    client.login(username=user.username, password='testpasswd')
    with open(submission_file, 'rb') as f:
        response = client.post(
            submission_url,
            {'file': f, 'challenge': challenge.short_name},
            format='multipart',
        )
    assert response.status_code == expected_response
    submissions = Submission.objects.all()
    if expected_response == 201:
        assert len(submissions) == 2
    else:
        assert len(submissions) == 0
    # We should not be able to download submissions
    for submission in Submission.objects.all():
        response = client.get(submission.file.url)
        assert response.status_code == 403
    # Cleanup
    for submission in submissions:
        filepath = submission.file.name
        submission.file.delete()
        try:
            os.removedirs(settings.MEDIA_ROOT + os.path.split(filepath)[0])
        except OSError:
            pass


# TODO: Validate the file and path
# TODO: Get the challenge name from the URL
# TODO: Check that the user is a participant of that challenge
