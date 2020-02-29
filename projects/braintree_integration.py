import braintree

BRAINTREE_MERCHANT_ID = 's52wdwywwgnhyfd2'
BRAINTREE_PUBLIC_KEY = 'qztjg8r3svpyj7zw'
BRAINTREE_PRIVATE_KEY = '98f3062e0086e4109bf1a836c222dcbb'

gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                braintree.Environment.Sandbox,
                merchant_id=BRAINTREE_MERCHANT_ID,
                public_key=BRAINTREE_PUBLIC_KEY,
                private_key=BRAINTREE_PRIVATE_KEY)
    )
