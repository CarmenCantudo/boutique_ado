from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from bag.contexts import bag_contents

import stripe


def checkout(request):
    """ From CI Boutique Ado """
    # Get Stripe public and secret keys from settings
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == 'POST':
        # Get user's shopping bag from their session data
        bag = request.session.get('bag', {})

        # Get form data from request
        form_data = {
            'full_name': request.POST['full_name'],
            'email': request.POST['email'],
            'phone_number': request.POST['phone_number'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
            'town_or_city': request.POST['town_or_city'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'county': request.POST['county'],
        }
        # Create an OrderForm with the form data
        order_form = OrderForm(form_data)
        # If the order form is valid: Save the order
        if order_form.is_valid():
            order = order_form.save()
            # Loop through each item in the shopping bag
            for item_id, item_data in bag.items():
                try:
                    # Get the product
                    product = Product.objects.get(id=item_id)
                    # If the item data is an integer
                    if isinstance(item_data, int):
                        # Create an OrderLineItem for the product and save it
                        order_line_item = OrderLineItem(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                        order_line_item.save()
                    else:
                        # Loop through each size and quantity in item data dictionary  # noqa
                        for size, quantity in item_data['items_by_size'].items():  # noqa
                            # Create OrderLineItem for product with size and quantity and save it  # noqa
                            order_line_item = OrderLineItem(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )
                            order_line_item.save()
                except Product.DoesNotExist:
                    # If product doesn't exist, display error message and redirect to shopping bag  # noqa
                    messages.error(request, (
                        "One of the products in your bag wasn't found in our database. "  # noqa
                        "Please call us for assistance!")
                    )
                    order.delete()
                    return redirect(reverse('view_bag'))

            # Set 'save_info' in session data if checkbox was checked
            request.session['save_info'] = 'save-info' in request.POST
            return redirect(reverse('checkout_success',
                                    args=[order.order_number]))
        else:
            # If order form is invalid, display error message
            messages.error(request, 'There was an error with your form. \
                Please double check your information.')
    else:
        # Get user's shopping bag from their session data
        bag = request.session.get('bag', {})
        if not bag:
            messages.error(request, "There's nothing in your bag at the moment")  # noqa
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


def checkout_success(request, order_number):
    """
    Handle successful checkouts
    """
    # Get user's save_info preference from their session data
    save_info = request.session.get('save_info')
    # Get order object that matches order number
    order = get_object_or_404(Order, order_number=order_number)
    # Display success message to user with order number and email address
    messages.success(request, f'Order successfully processed! \
        Your order number is {order_number}. A confirmation \
        email will be sent to {order.email}.')

    # Remove shopping bag from session data
    if 'bag' in request.session:
        del request.session['bag']

    # Render checkout success template with order details
    template = 'checkout/checkout_success.html'
    context = {
        'order': order,
    }

    return render(request, template, context)
