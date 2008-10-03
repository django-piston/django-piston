from django import forms

class Form(forms.Form):
    pass
    
class ModelForm(forms.ModelForm):
    def merge_from_initial(self):
        self.data._mutable = True
        filt = lambda v: v not in self.data.keys()
        for field in filter(filt, getattr(self.Meta, 'fields', ())):
            self.data[field] = self.initial.get(field, None)

