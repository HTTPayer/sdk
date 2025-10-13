from httpayer import HTTPayerClient

def main(urls):

    """Test the HTTPayerClient with multiple URLs.
    This function sends GET requests to the provided URLs and prints the response headers,
    status codes, and response bodies. It uses the explicit methods, meaning there is no call to request() first,
    just a call to the HTTPayer proxy server directly.

    Args:
        urls (list): A list of URLs to test with the HTTPayerClient.

    """

    responses = []

    for url in urls:
        print(f'processing {url}...')

        client = HTTPayerClient()

        # We can simulate calling the endpoint to get payment instructions w/ simulate=True
        # This is an explicit call to the simulate_invoice method
        sim_response = client.simulate_invoice("GET", url)
        print("simulated response:", sim_response.json())

        # Now we can pay the invoice and get the actual resource
        # This is an explicit call to the pay_invoice method
        response = client.pay_invoice("GET", url)

        print(f'response headers: {response.headers}')  # contains the x-payment-response header
        print(f'response status code: {response.status_code}')  # should be 200 OK
        print(f'response text: {response.text}')  # contains the actual resource
        try:
            print(f'response json: {response.json()}')  # if the response is JSON, print it
        except ValueError:
            print("Response content is not valid JSON")

        responses.append(response)

    return responses

if __name__ == "__main__":
    print(f'starting test1...')
    urls = ["https://www.x402.org/protected"]
    main(urls)
