from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from bag.contexts import bag_contents

import stripe


def checkout(request):
    """ From CI Boutique Ado """
    # Get Stripe public and secret keys from settings
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    # Get user's shopping bag from their session data
    bag = request.session.get('bag', {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse('products'))

    # Get bag contents and calculate total price
    current_bag = bag_contents(request)
    total = current_bag['grand_total']
    # Convert total price to the smallest unit of currency
    stripe_total = round(total * 100)
    stripe.api_key = stripe_secret_key
    # Create a new payment intent with the Stripe API
    intent = stripe.PaymentIntent.create(
        amount=stripe_total,
        currency=settings.STRIPE_CURRENCY,
    )

    # Create a new order form
    order_form = OrderForm()

    # If Stripe public key is missing, display a warning message
    if not stripe_public_key:
        messages.warning(request, 'Stripe public key is missing. \
            Did you forget to set it in your environment?')

    template = 'checkout/checkout.html'
    context = {
        'order_form': order_form,
        'stripe_public_key': stripe_public_key,
        'client_secret': intent.client_secret,
    }

    return render(request, template, context)
