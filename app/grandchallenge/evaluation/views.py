from datetime import timedelta, datetime
from typing import Dict

from django.contrib.messages.views import SuccessMessageMixin
from django.core.files import File
from django.db.models import Q
from django.utils import timezone
from django.views.generic import CreateView, ListView, DetailView, UpdateView

from grandchallenge.core.permissions.mixins import (
    UserIsChallengeAdminMixin, UserIsChallengeParticipantOrAdminMixin
)
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.forms import (
    MethodForm, SubmissionForm, ConfigForm, LegacySubmissionForm
)
from grandchallenge.evaluation.models import (
    Result, Submission, Job, Method, Config,
)


class ConfigUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    form_class = ConfigForm
    success_message = "Configuration successfully updated"

    def get_object(self, queryset=None):
        challenge = self.request.challenge
        return challenge.evaluation_config


class MethodCreate(UserIsChallengeAdminMixin, CreateView):
    model = Method
    form_class = MethodForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.challenge = self.request.challenge
        uploaded_file = form.cleaned_data['chunked_upload'][0]
        with uploaded_file.open() as f:
            form.instance.image.save(uploaded_file.name, File(f))
        return super().form_valid(form)


class MethodList(UserIsChallengeAdminMixin, ListView):
    model = Method

    def get_queryset(self):
        queryset = super(MethodList, self).get_queryset()
        return queryset.filter(challenge=self.request.challenge)


class MethodDetail(UserIsChallengeAdminMixin, DetailView):
    model = Method


class SubmissionCreateBase(SuccessMessageMixin, CreateView):
    """
    This class has no permissions, do not use it directly! See the subclasses
    """
    model = Submission
    success_message = (
        "Your submission was successful. "
        "Your result will appear on the leaderboard when it is ready."
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        config = Config.objects.get(challenge=self.request.challenge)

        kwargs.update(
            {
                'display_comment_field': config.allow_submission_comments,
                'allow_supplementary_file': config.allow_supplementary_file,
                'require_supplementary_file': config.require_supplementary_file,
                'supplementary_file_label': config.supplementary_file_label,
                'supplementary_file_help_text': config.supplementary_file_help_text,
            }
        )

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = Config.objects.get(challenge=self.request.challenge)

        context.update(
            self.get_next_submission(max_subs=config.daily_submission_limit)
        )

        pending_jobs = Job.objects.filter(
            challenge=self.request.challenge,
            submission__creator=self.request.user,
            status__in=(Job.PENDING, Job.STARTED),
        ).count()

        context.update({'pending_jobs': pending_jobs})

        return context

    def get_next_submission(
        self,
        *,
        max_subs: int,
        period: timedelta=timedelta(days=1),
        now: datetime=None
    ) -> Dict:
        """
        Determines the number of submissions left for the user in a given time
        period, and when they can next submit.

        :return: A dictionary containing remaining_submissions (int) and
        next_submission_at (datetime)
        """
        if now is None:
            now = timezone.now()

        subs = Submission.objects.filter(
            challenge=self.request.challenge,
            creator=self.request.user,
            created__gte=now - period,
        ).order_by(
            '-created'
        )

        try:
            next_sub_at = subs[max_subs - 1].created + period
        except (IndexError, AssertionError):
            next_sub_at = now

        return {
            'remaining_submissions': max_subs - len(subs),
            'next_submission_at': next_sub_at,
        }

    def form_valid(self, form):

        if form.instance.creator is None:
            form.instance.creator = self.request.user

        form.instance.challenge = self.request.challenge

        uploaded_file = form.cleaned_data['chunked_upload'][0]

        with uploaded_file.open() as f:
            form.instance.file.save(uploaded_file.name, File(f))

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'evaluation:job-list',
            kwargs={'challenge_short_name': self.object.challenge.short_name},
        )


class SubmissionCreate(
    UserIsChallengeParticipantOrAdminMixin, SubmissionCreateBase
):
    form_class = SubmissionForm


class LegacySubmissionCreate(UserIsChallengeAdminMixin, SubmissionCreateBase):
    form_class = LegacySubmissionForm

    def get_next_submission(
        self,
        *,
        max_subs: int,
        period: timedelta = timedelta(days=1),
        now: datetime = None
    ):
        """
        Admins should always be able to upload legacy results, so set the
        remaining submissions to infinite.
        """
        if now is None:
            now = timezone.now()

        return {
            'remaining_submissions': float('Inf'),
            'next_submission_at': now,
        }


class SubmissionList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Submission

    def get_queryset(self):
        """ Admins see everything, participants just their submissions """
        queryset = super(SubmissionList, self).get_queryset()
        challenge = self.request.challenge
        if challenge.is_admin(self.request.user):
            return queryset.filter(challenge=self.request.challenge)

        else:
            return queryset.filter(
                Q(challenge=self.request.challenge),
                Q(creator__pk=self.request.user.pk),
            )


class SubmissionDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their submissions
    model = Submission


class JobCreate(UserIsChallengeAdminMixin, CreateView):
    model = Job
    fields = '__all__'


class JobList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Job

    def get_queryset(self):
        """ Admins see everything, participants just their jobs """
        queryset = super(JobList, self).get_queryset()
        queryset = queryset.select_related('result')
        challenge = self.request.challenge
        if challenge.is_admin(self.request.user):
            return queryset.filter(challenge=self.request.challenge)

        else:
            return queryset.filter(
                Q(challenge=self.request.challenge),
                Q(submission__creator__pk=self.request.user.pk),
            )


class JobDetail(UserIsChallengeAdminMixin, DetailView):
    # TODO - if participant: list only their jobs
    model = Job


class ResultList(ListView):
    model = Result

    def get_queryset(self):
        queryset = super(ResultList, self).get_queryset()
        queryset = queryset.select_related(
            'job__submission__creator__user_profile'
        )
        return queryset.filter(
            Q(challenge=self.request.challenge), Q(public=True)
        )


class ResultDetail(DetailView):
    model = Result


class ResultUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView):
    model = Result
    fields = ('public',)
    success_message = ('Result successfully updated.')
