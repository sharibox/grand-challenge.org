import uuid

from django.contrib.auth.models import User
from django.db import models
from social_django.fields import JSONField

from evaluation.validators import MimeTypeValidator


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified
    times
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Result(UUIDModel):
    """
    Stores individual results for a challenges
    """
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    metrics = JSONField(default=dict)

    public = models.BooleanField(default=True)


def result_screenshot_path(instance, filename):
    return f'evaluation/{instance.challenge.id}/screenshots/' \
           f'{instance.result.id}/{filename}'


class ResultScreenshot(UUIDModel):
    """
    Stores a screenshot that is generated during an evaluation
    """
    result = models.ForeignKey('Result',
                               on_delete=models.CASCADE)

    image = models.ImageField(upload_to=result_screenshot_path)


def method_container_path(instance, filename):
    return f'evaluation/{instance.challenge.id}/methods/' \
           f'{instance.method.id}/{filename}'


class Method(UUIDModel):
    """
    Stores the methods for performing an evaluation
    """
    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    container = models.FileField(upload_to=method_container_path,
                                 validators=[MimeTypeValidator(
                                     allowed_types=(
                                         'application/x-tarbinary',))],
                                 help_text='Tar archive of the container '
                                           'image produced from the command '
                                           '`docker save IMAGE > '
                                           'IMAGE.tar`. See '
                                           'https://docs.docker.com/engine/reference/commandline/save/',
                                 )

    class Meta:
        unique_together = (("challenge", "created"),)


def challenge_submission_path(instance, filename):
    return f'evaluation/{instance.challenge.id}/submissions/' \
           f'{instance.user.id}/' \
           f'{instance.created.strftime("%Y%m%d%H%M%S")}/' \
           f'{filename}'


class Submission(UUIDModel):
    """
    Stores files for evaluation
    """
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    file = models.FileField(upload_to=challenge_submission_path,
                            validators=[MimeTypeValidator(
                                allowed_types=('application/zip',))])


class Job(UUIDModel):
    """
    Stores information about a job for a given upload
    """

    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, 'The task is waiting for execution'),
        (STARTED, 'The task has been started'),
        (RETRY, 'The task is to be retried, possibly because of failure'),
        (FAILURE,
         'The task raised an exception, or has exceeded the retry limit'),
        (SUCCESS, 'The task executed successfully'),
        (CANCELLED, 'The task was cancelled')
    )

    submission = models.ForeignKey('Submission',
                                   null=True,
                                   on_delete=models.SET_NULL)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=PENDING)

    status_history = JSONField(default=dict)

    output = models.TextField()


class StagedFile(UUIDModel):
    """
    Files uploaded but not committed to other forms.
    """
    timeout = models.DateTimeField(blank=False)
    file = models.FileField(blank=False)
    annotations = models.TextField(null=True)
