from django import forms
from .models import Profile, Label

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'bio', 'location', 'birth_date', 'avatar', 'calendar_public']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter your last name'}),
            'calendar_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['calendar_public'].widget.attrs['class'] = 'form-check-input'

class LabelForm(forms.ModelForm):
    COLOR_CHOICES = [
        ('#FF0000', 'Red'),
        ('#FFA500', 'Orange'),
        ('#FFFF00', 'Yellow'),
        ('#008000', 'Green'),
        ('#0000FF', 'Blue'),
        ('#4B0082', 'Indigo'),
        ('#800080', 'Purple'),
        ('#FF69B4', 'Pink'),
        ('#A52A2A', 'Brown'),
        ('#808080', 'Gray'),
    ]

    color = forms.ChoiceField(
        choices=COLOR_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'color-radio-group'})
    )

    class Meta:
        model = Label
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter label name'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        user = self.user or getattr(self.instance, 'user', None)
        if user and Label.objects.filter(user=user, name=name).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
            raise forms.ValidationError('You already have a label with this name.')
        return name 