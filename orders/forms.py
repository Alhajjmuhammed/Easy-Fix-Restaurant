from django import forms
from restaurant.models import TableInfo
from .models import Order

class TableSelectionForm(forms.Form):
    table_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Enter table number',
            'required': True,
            'style': 'font-size: 1.5rem; font-weight: bold;'
        }),
        label='Table Number'
    )
    
    def clean_table_number(self):
        table_number = self.cleaned_data['table_number'].strip()
        
        try:
            table = TableInfo.objects.get(tbl_no=table_number)
            if not table.is_available:
                raise forms.ValidationError('This table is currently not available.')
        except TableInfo.DoesNotExist:
            raise forms.ValidationError('Invalid table number. Please check and try again.')
        
        return table_number

class OrderForm(forms.Form):
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Any special instructions for your order? (Optional)'
        }),
        label='Special Instructions'
    )

class OrderStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class CancelOrderForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please provide a reason for cancelling this order...',
            'required': True
        }),
        label='Cancellation Reason'
    )
