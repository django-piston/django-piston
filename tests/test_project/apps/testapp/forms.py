from django import forms


class EchoForm(forms.Form):
    msg = forms.CharField(max_length=128)

