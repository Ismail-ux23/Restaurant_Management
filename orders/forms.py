from django import forms

from tables.models import Table
from .models import Order, Review


class CheckoutForm(forms.Form):
    order_type = forms.ChoiceField(choices=Order.ORDER_TYPE_CHOICES)
    table = forms.ModelChoiceField(
        queryset=Table.objects.filter(status="available"), required=False,
        help_text="Required for dine-in orders."
    )
    delivery_address = forms.CharField(widget=forms.Textarea, required=False)
    coupon_code = forms.CharField(max_length=30, required=False)
    payment_method = forms.ChoiceField(choices=[("cash", "Cash"), ("card", "Card")])

    def clean(self):
        cleaned = super().clean()
        order_type = cleaned.get("order_type")
        if order_type == "dine_in" and not cleaned.get("table"):
            raise forms.ValidationError("Please select a table for a dine-in order.")
        if order_type == "delivery" and not cleaned.get("delivery_address"):
            raise forms.ValidationError("Please provide a delivery address.")
        return cleaned


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"rating": forms.Select(choices=[(i, f"{i} star{'s' if i != 1 else ''}") for i in range(1, 6)])}


class StatusChangeForm(forms.Form):
    note = forms.CharField(max_length=255, required=False)
