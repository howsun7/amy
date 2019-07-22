from django_select2.forms import (
    Select2Widget as DS2_Select2Widget,
    Select2MultipleWidget as DS2_Select2MultipleWidget,
    ModelSelect2Widget as DS2_ModelSelect2Widget,
    ModelSelect2MultipleWidget as DS2_ModelSelect2MultipleWidget,
    Select2TagWidget as DS2_Select2TagWidget,
)
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django import forms


GHUSERNAME_MAX_LENGTH_VALIDATOR = MaxLengthValidator(39,
    message='Maximum allowed username length is 39 characters.',
)
# according to https://stackoverflow.com/q/30281026,
# GH username can only contain alphanumeric characters and
# hyphens (but not consecutive), cannot start or end with
# a hyphen, and can't be longer than 39 characters
GHUSERNAME_REGEX_VALIDATOR = RegexValidator(
    # regex inspired by above StackOverflow thread
    regex=r'^([a-zA-Z\d](?:-?[a-zA-Z\d])*)$',
    message='This is not a valid GitHub username.',
)


class NullableGithubUsernameField(models.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('default', '')
        # max length of the GH username is 39 characters
        kwargs.setdefault('max_length', 39)
        super().__init__(**kwargs)

    default_validators = [
        GHUSERNAME_MAX_LENGTH_VALIDATOR,
        GHUSERNAME_REGEX_VALIDATOR,
    ]


class RadioSelectWithOther(forms.RadioSelect):
    """A RadioSelect widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class CheckboxSelectMultipleWithOthers(forms.CheckboxSelectMultiple):
    """A multiple choice widget that should render additional field ('Other').

    We have a number of occurences of two model fields bound together: one
    containing predefined set of choices, the other being a text input for
    other input user wants to choose instead of one of our predefined options.

    This widget should help with rendering two widgets in one table row."""

    other_field = None  # to be bound later

    def __init__(self, other_field_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.other_field_name = other_field_name


class RadioSelectFakeMultiple(forms.RadioSelect):
    """Pretend to be a radio-select with multiple selection possible. This
    is intended to 'fool' Django into thinking that user selected 1 item on
    a multi-select item list."""
    allow_multiple_selected = True


#------------------------------------------------------------

class Select2BootstrapMixin:
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs.setdefault('data-theme', 'bootstrap4')
        return attrs


class Select2NoMinimumInputLength:
    def build_attrs(self, *args, **kwargs):
        # Let's set up the minimum input length first!
        # It will overwrite `setdefault('data-minimum-input-length')` from
        # other mixins.
        self.attrs.setdefault('data-minimum-input-length', 0)
        attrs = super().build_attrs(*args, **kwargs)
        return attrs



class Select2Widget(Select2BootstrapMixin, DS2_Select2Widget):
    pass


class Select2MultipleWidget(Select2BootstrapMixin, DS2_Select2MultipleWidget):
    pass


class ModelSelect2Widget(Select2BootstrapMixin, Select2NoMinimumInputLength,
                         DS2_ModelSelect2Widget):
    pass


class ModelSelect2MultipleWidget(Select2BootstrapMixin,
                                 Select2NoMinimumInputLength,
                                 DS2_ModelSelect2MultipleWidget):
    pass


class Select2TagWidget(Select2BootstrapMixin, DS2_Select2TagWidget):
    pass
