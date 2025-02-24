from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_countries.fields import CountryField

from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.fields import (
    ModelSelect2MultipleWidget,
    RadioSelectWithOther,
    Select2Widget,
)
from workshops.forms import BootstrapHelper
from workshops.models import (
    Event,
    GenderMixin,
    Language,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)


class AssignmentForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label="Assigned to:",
        required=False,
        queryset=Person.objects.filter(
            Q(is_superuser=True) | Q(groups__name="administrators")
        ).distinct(),
        widget=Select2Widget(),
    )
    helper = BootstrapHelper(
        add_submit_button=False,
        add_cancel_button=False,
        wider_labels=True,
        use_get_method=True,
        form_id="assignment-form",
    )


class AutoUpdateProfileForm(forms.ModelForm):
    username = forms.CharField(disabled=True, required=False)
    email = forms.CharField(
        disabled=True,
        required=False,
        label=Person._meta.get_field("email").verbose_name,
        help_text=Person._meta.get_field("email").help_text,
    )
    github = forms.CharField(
        disabled=True,
        required=False,
        help_text="If you want to change your github username, please email "
        'us at <a href="mailto:team@carpentries.org">'
        "team@carpentries.org</a>.",
    )

    country = CountryField().formfield(
        required=False,
        help_text="Your country of residence.",
        widget=Select2Widget,
    )

    languages = forms.ModelMultipleChoiceField(
        label="Languages",
        required=False,
        queryset=Language.objects.all(),
        widget=ModelSelect2MultipleWidget(data_view="language-lookup"),
    )

    class Meta:
        model = Person
        fields = [
            "personal",
            "middle",
            "family",
            "email",
            "secondary_email",
            "gender",
            "gender_other",
            "country",
            "airport",
            "github",
            "twitter",
            "url",
            "username",
            "affiliation",
            "domains",
            "lessons",
            "languages",
            "occupation",
            "orcid",
        ]
        readonly_fields = (
            "username",
            "github",
        )
        widgets = {
            "gender": RadioSelectWithOther("gender_other"),
            "domains": forms.CheckboxSelectMultiple(),
            "lessons": forms.CheckboxSelectMultiple(),
            "airport": Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        form_tag = kwargs.pop("form_tag", True)
        add_submit_button = kwargs.pop("add_submit_button", True)
        super().__init__(*args, **kwargs)
        self.helper = BootstrapHelper(
            add_cancel_button=False,
            form_tag=form_tag,
            add_submit_button=add_submit_button,
        )

        # set up a layout object for the helper
        self.helper.layout = self.helper.build_default_layout(self)

        # set up `*WithOther` widgets so that they can display additional
        # fields inline
        self["gender"].field.widget.other_field = self["gender_other"]

        # remove additional fields
        self.helper.layout.fields.remove("gender_other")

    def clean(self):
        super().clean()
        errors = dict()

        # 1: require "other gender" field if "other" was selected in
        # "gender" field
        gender = self.cleaned_data.get("gender", "")
        gender_other = self.cleaned_data.get("gender_other", "")
        if gender == GenderMixin.OTHER and not gender_other:
            errors["gender"] = ValidationError("This field is required.")
        elif gender != GenderMixin.OTHER and gender_other:
            errors["gender"] = ValidationError(
                'If you entered data in "Other" field, please select that ' "option."
            )

        # raise errors if any present
        if errors:
            raise ValidationError(errors)


class SendHomeworkForm(forms.ModelForm):
    url = forms.URLField(label="URL")
    requirement = forms.ModelChoiceField(
        queryset=TrainingRequirement.objects.filter(name__endswith="Homework"),
        label="Type",
        required=True,
    )

    helper = BootstrapHelper(add_cancel_button=False)

    class Meta:
        model = TrainingProgress
        fields = [
            "requirement",
            "url",
        ]


class SearchForm(forms.Form):
    """Represent general searching form."""

    term = forms.CharField(label="Term", max_length=100)
    no_redirect = forms.BooleanField(required=False, initial=False)
    helper = BootstrapHelper(add_cancel_button=False, use_get_method=True)


class SignupForRecruitmentForm(forms.ModelForm):
    user_notes = forms.CharField(
        required=False, widget=forms.Textarea, label="Your notes"
    )
    helper = BootstrapHelper(
        submit_label="Submit my interest in teaching this workshop",
        add_cancel_button=False,
    )

    class Meta:
        model = InstructorRecruitmentSignup
        fields = [
            "user_notes",
        ]

    def __init__(self, *args, **kwargs):
        self.person: Person = kwargs.pop("person")
        self.recruitment: InstructorRecruitment = kwargs.pop("recruitment")
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Check if user has any instructor roles for events taking place at the same
        # time of this event.
        event: Event = self.recruitment.event
        if (
            event.start
            and event.end
            and (
                conflicting_tasks := Task.objects.filter(
                    person=self.person,
                    role__name="instructor",
                    event__start__lte=event.end,
                    event__end__gte=event.start,
                )
            )
        ):
            # error not bound to any particular field
            raise ValidationError(
                "Selected event dates conflict with events: "
                f"{', '.join(task.event.slug for task in conflicting_tasks)}"
            )
