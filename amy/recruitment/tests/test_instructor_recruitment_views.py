from datetime import date
from unittest import mock

from django.test import override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from autoemails.actions import NewInstructorAction
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from recruitment.filters import InstructorRecruitmentFilter
from recruitment.forms import (
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
)
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
import recruitment.views
from recruitment.views import (
    InstructorRecruitmentCreate,
    InstructorRecruitmentDetails,
    InstructorRecruitmentList,
    InstructorRecruitmentSignupChangeState,
)
from workshops.models import (
    Event,
    Language,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    WorkshopRequest,
)
from workshops.tests.base import TestBase


class TestInstructorRecruitmentListView(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentList()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.view_instructorrecruitment"
        )
        self.assertEqual(view.title, "Recruitment processes")
        self.assertEqual(view.filter_class, InstructorRecruitmentFilter)
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_list.html"
        )
        self.assertNotEqual(view.queryset, None)  # it's a complicated query

    def test_get_filter_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request)
        # Act
        data = view.get_filter_data()
        # Assert
        self.assertIn("assigned_to", data.keys())
        self.assertEqual(data["assigned_to"], request.user.pk)

    def test_get_context_data_empty(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request, object_list=[], filter=None)
        # Act
        context = view.get_context_data()
        # Assert
        self.assertIn("personal_conflicts", context.keys())
        self.assertEqual(
            list(context["personal_conflicts"]), list(Person.objects.none())
        )

    def test_get_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request, object_list=[], filter=None)
        host = Organization.objects.first()
        event = Event.objects.create(slug="test-event", host=host)
        recruitment = InstructorRecruitment.objects.create(event=event)
        person = Person.objects.create(username="test_user")
        InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, interest="session"
        )
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(list(context["personal_conflicts"]), [person])

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2022, 1, 22),
        )
        recruitment = InstructorRecruitment.objects.create(
            assigned_to=self.admin,
            event=event,
            notes="Test notes",
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, interest="session"
        )
        # Act
        response = self.client.get(reverse("all_instructorrecruitment"))
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [recruitment])
        self.assertEqual(
            list(
                response.context["object_list"][0].instructorrecruitmentsignup_set.all()
            ),
            [signup],
        )


class TestInstructorRecruitmentCreateView(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentCreate()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.add_instructorrecruitment"
        )
        self.assertEqual(view.model, InstructorRecruitment)
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_add.html"
        )
        self.assertEqual(view.form_class, InstructorRecruitmentCreateForm)
        self.assertEqual(view.event, None)

    def test_get_other_object(self) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        object = view.get_other_object()
        # Assert
        self.assertEqual(event, object)

    def test_get(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.get(request)
        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.event, event)
        mock_super().get.assert_called_once_with(request)

    def test_post(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.post(request)
        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.event, event)
        mock_super().post.assert_called_once_with(request)

    def test_get_form_kwargs(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(request=request)
        view.event = event
        # Act
        kwargs = view.get_form_kwargs()
        # Assert
        self.assertEqual(kwargs, {"initial": {}, "prefix": "instructorrecruitment"})

    def test_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        view = InstructorRecruitmentCreate(request=request, object=None)
        view.event = event
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(
            context,
            {
                "title": "Begin Instructor Selection Process for test-event",
                "event": event,
                "event_dates": "Dec 29, 2021-???",
                "view": view,
                "model": InstructorRecruitment,
                # it needs to be the same instance, otherwise the test fails
                "form": context["form"],
            },
        )

    def test_get_initial(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        workshop_request = WorkshopRequest.objects.create(
            event=event,
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            location="Scotland",
            country="GB",
            audience_description="Students of Hogwarts",
            user_notes="Only Gryffindor allowed.",
            number_attendees="10-40",
            administrative_fee="nonprofit",
            language=Language.objects.get(name="English"),
        )
        view = InstructorRecruitmentCreate(request=request, object=None)
        view.event = event
        # Act
        initial = view.get_initial()
        # Assert
        self.assertEqual(
            initial,
            {
                "notes": f"{workshop_request.audience_description}\n\n"
                f"{workshop_request.user_notes}",
            },
        )

    def test_form_valid(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        mock_form = mock.MagicMock()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(request=request)
        view.event = event
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.form_valid(mock_form)
        # Assert
        mock_form.save.assert_called_once_with(commit=False)
        self.assertEqual(view.object.event, event)
        mock_super().form_valid.assert_called_once_with(mock_form)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        data = {"instructorrecruitment-notes": "Test notes"}
        # Act
        response = self.client.post(
            reverse("instructorrecruitment_add", args=[event.pk]), data, follow=True
        )
        recruitment: InstructorRecruitment = response.context["object"]
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.redirect_chain,
            [
                (
                    reverse(
                        "instructorrecruitment_details",
                        args=[recruitment.pk],
                    ),
                    302,
                )
            ],
        )
        self.assertEqual(recruitment.status, "o")
        self.assertEqual(recruitment.notes, "Test notes")
        self.assertEqual(recruitment.event, event)


class TestInstructorRecruitmentDetailsView(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentDetails()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.view_instructorrecruitment"
        )
        self.assertNotEqual(view.queryset, None)  # actual qs is quite lengthy
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_details.html"
        )

    def test_context_data(self) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event,
            notes="Test notes",
        )
        view = InstructorRecruitmentDetails(
            kwargs={"pk": recruitment.pk}, object=recruitment
        )
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(
            context,
            {
                "title": str(recruitment),
                "instructorrecruitment": recruitment,
                "object": recruitment,
                "view": view,
            },
        )

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event,
            notes="Test notes",
        )
        # Act
        response = self.client.get(
            reverse("instructorrecruitment_details", args=[recruitment.pk])
        )
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], recruitment)


class TestInstructorRecruitmentSignupChangeState(FakeRedisTestCaseMixin, TestBase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = recruitment.views.scheduler
        self._saved_redis_connection = recruitment.views.redis_connection
        # overwrite them
        recruitment.views.scheduler = self.scheduler
        recruitment.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        recruitment.views.scheduler = self._saved_scheduler
        recruitment.views.redis_connection = self._saved_redis_connection

    def _prepare_email_automation_data(self) -> None:
        self.automated_email_tag = Tag.objects.create(
            name="automated-email", priority=0
        )
        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="new-instructor", template=template)

    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentSignupChangeState()
        # Assert
        self.assertEqual(view.form_class, InstructorRecruitmentSignupChangeStateForm)

    def test_get_object(self) -> None:
        # Arrange
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        # Act
        with mock.patch("recruitment.views.InstructorRecruitmentSignup") as mock_signup:
            view.get_object()
        # Assert
        mock_signup.objects.get.assert_called_once_with(pk=pk)

    def test_get_success_url__safe_next_provided(self) -> None:
        # Arrange
        safe_next = "/asdasd"
        request = RequestFactory().post("/", {"next": safe_next})
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
            view.post(request)
        # Act
        result = view.get_success_url()
        # Assert
        self.assertEqual(result, safe_next)

    def test_get_success_url__unsafe_next_provided(self) -> None:
        # Arrange
        unsafe_next = "https://google.com/"
        default_success_url = reverse("all_instructorrecruitment")
        request = RequestFactory().post("/", {"next": unsafe_next})
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
            view.post(request)
        # Act
        result = view.get_success_url()
        # Assert
        self.assertEqual(result, default_success_url)

    def test_get_success_url__next_not_provided(self) -> None:
        # Arrange
        default_success_url = reverse("all_instructorrecruitment")
        request = RequestFactory().post("/")
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
            view.post(request)
        # Act
        result = view.get_success_url()
        # Assert
        self.assertEqual(result, default_success_url)

    def test_form_invalid__redirects_to_success_url(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
            view.post(request)
        # Act
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_success_url"
        ) as mock_get_success_url:
            mock_get_success_url.return_value = "/"
            result = view.form_invalid(mock.MagicMock())
        # Assert
        mock_get_success_url.assert_called_once()
        self.assertEqual(result.status_code, 302)

    def test_form_valid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentSignupChangeState(
            object=mock_object, request=request
        )
        view.add_instructor_task = mock.MagicMock()
        view.remove_instructor_task = mock.MagicMock()
        data = {"action": "confirm"}
        form = InstructorRecruitmentSignupChangeStateForm(data)
        form.is_valid()
        # Act
        view.form_valid(form)
        # Assert
        self.assertEqual(mock_object.state, "a")
        mock_object.save.assert_called_once()
        view.add_instructor_task.assert_called_once_with(
            mock_object.person, mock_object.recruitment.event
        )
        view.remove_instructor_task.assert_not_called()

    def test_add_instructor_task(self) -> None:
        # Arrange
        super()._setUpRoles()
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState(request=request)
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        organization = self.org_alpha
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        event.tags.add(self.automated_email_tag)
        # Act
        task = view.add_instructor_task(person, event)
        # Assert
        self.assertTrue(task.pk)
        self.assertTrue(NewInstructorAction.check(task))
        self.assertTrue(task.rq_jobs.all())

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())
        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()
        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

    def test_remove_instructor_task(self) -> None:
        # Arrange
        super()._setUpRoles()
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState(request=request)
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        role = Role.objects.get(name="instructor")
        task = Task.objects.create(person=person, event=event, role=role)
        # Act
        view.remove_instructor_task(person, event)
        # Assert
        with self.assertRaises(Task.DoesNotExist):
            task.refresh_from_db()

    def test_post__form_valid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState()
        # Act
        # TODO: switch syntax for multiple context managers in Python 3.10+
        # https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_object"
        ) as mock_get_object, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_form"
        ) as mock_get_form, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_valid"
        ) as mock_form_valid, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_invalid"
        ) as mock_form_invalid:
            mock_get_form.return_value.is_valid.return_value = True
            view.post(request)
        # Assert
        mock_get_object.assert_called_once()
        mock_get_form.assert_called_once()
        mock_get_form.return_value.is_valid.assert_called_once()
        mock_form_valid.assert_called_once_with(mock_get_form.return_value)
        mock_form_invalid.assert_not_called()

    def test_post__form_invalid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState()
        # Act
        # TODO: switch syntax for multiple context managers in Python 3.10+
        # https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_object"
        ) as mock_get_object, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_form"
        ) as mock_get_form, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_valid"
        ) as mock_form_valid, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_invalid"
        ) as mock_form_invalid:
            mock_get_form.return_value.is_valid.return_value = False
            view.post(request)
        # Assert
        mock_get_object.assert_called_once()
        mock_get_form.assert_called_once()
        mock_get_form.return_value.is_valid.assert_called_once()
        mock_form_valid.assert_not_called()
        mock_form_invalid.assert_called_once_with(mock_get_form.return_value)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event, notes="Test notes"
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person
        )
        role = Role.objects.create(name="instructor")
        data = {"action": "confirm"}
        url = reverse("instructorrecruitmentsignup_changestate", args=[signup.pk])
        success_url = reverse("all_instructorrecruitment")
        # Act
        response = self.client.post(url, data, follow=False)
        signup.refresh_from_db()
        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(signup.state, "a")
        self.assertTrue(Task.objects.get(event=event, person=person, role=role))
