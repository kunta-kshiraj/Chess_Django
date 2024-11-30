# from django import forms
# from django.core import validators
# from django.contrib.auth.models import User

# from django import forms
# from django.core import validators
# from django.contrib.auth.models import User
# from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth import get_user_model


# class ChessForm(forms.Form):
#     start_position=forms.CharField(min_length=2, max_length=2, strip=True)
#     end_position= forms.CharField(min_length=2, max_length=3, strip=True)


# # Validator function for checking valid chess positions
# def validate_chess_position(value):
#     """
#     Validates if the input is a valid chessboard position.
#     A valid position should be in the form of 'e2', 'a1', etc.
#     """
#     if len(value) != 2 or not (value[0] in "abcdefgh") or not (value[1] in "12345678"):
#         raise forms.ValidationError("Enter a valid chessboard position (e.g., 'e2').")


# # Form for handling chess moves
# class MoveForm(forms.Form):
#     """
#     MoveForm takes in the source and destination positions for a chess move.
#     Validations ensure that input is a valid chess position.
#     """
#     source = forms.CharField(
#         max_length=2,
#         strip=True,
#         widget=forms.TextInput(attrs={
#             'placeholder': 'e2',
#             'class': 'form-control',
#             'style': 'font-size:small'
#         }),
#         validators=[
#             validators.MinLengthValidator(2),
#             validators.MaxLengthValidator(2),
#             validate_chess_position
#         ]
#     )
#     destination = forms.CharField(
#         max_length=2,
#         strip=True,
#         widget=forms.TextInput(attrs={
#             'placeholder': 'e4',
#             'class': 'form-control',
#             'style': 'font-size:small'
#         }),
#         validators=[
#             validators.MinLengthValidator(2),
#             validators.MaxLengthValidator(2),
#             validate_chess_position
#         ]
#     )



from django import forms
from .models import JournalEntry
from django.core import validators
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

# Validator function for checking valid chess positions
def validate_chess_position(value):
    """
    Validates if the input is a valid chessboard move (e.g., 'e2e4').
    The first two characters are the source position, and the last two are the destination.
    """
    if len(value) != 4:
        raise forms.ValidationError("Move must consist of exactly 4 characters (e.g., 'e2e4').")

    start_pos = value[:2]
    end_pos = value[2:]

    # Validate both start and end positions
    for pos in [start_pos, end_pos]:
        if not (pos[0] in "abcdefgh" and pos[1] in "12345678"):
            raise forms.ValidationError(f"Invalid position '{pos}'. Please enter a valid chessboard position (e.g., 'e2').")

class MoveForm(forms.Form):
    """
    MoveForm takes in a single field, move_position, which contains both
    the source and destination positions in a single input (e.g., 'e2e4').
    """
    move_position = forms.CharField(
        max_length=4,
        strip=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e2e4',
            'class': 'form-control',
            'style': 'font-size:small'
        }),
        validators=[
            validators.MinLengthValidator(4),
            validators.MaxLengthValidator(4),
            validate_chess_position
        ]
    )

# Form for handling combined chess moves
class ChessForm(forms.Form):
    """
    ChessForm now accepts a single input move_position that consists of both
    source and destination positions combined (e.g., 'e2e4').
    """
    move_position = forms.CharField(
        max_length=4,
        strip=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'e2e4',
            'class': 'form-control',
            'style': 'font-size:small'
        }),
        validators=[
            validators.MinLengthValidator(4),
            validators.MaxLengthValidator(4),
            validate_chess_position
        ]
    )

class JoinForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    email = forms.CharField(widget=forms.TextInput(attrs={'size': '30'}))
    class Meta():
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password')
        help_texts = {'username': None}

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())


class JournalForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['description', 'entry']
        widgets = {
            'entry': forms.Textarea(attrs={'rows': 5, 'cols': 50}),
        }
