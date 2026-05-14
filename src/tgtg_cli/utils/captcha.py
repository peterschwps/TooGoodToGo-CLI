import capsolver


def solve_datadome(
    capsolver_api_key: str, website_url: str, captcha_url: str, proxy: str
):
    """
    Solves a Datadome captcha using CapSolver.
    IMPORTANT: userAgent has to remaind hardcoded as is, other user agents
               don't work reliably.

    Args:
        capsolver_api_key (str): CapSolver API key.
        website_url (str): URL of the website that the captcha is on.
        captcha_url (str): URL of the datadome captcha.
        proxy (str): Proxy to use for solving the captcha. Needs to be in
                     format: "ip:port:username:password".

    Returns:
        dict: Datadome cookie of the solved captcha for further requests.
    """
    # IMPORTANT: leave userAgent as is, most other user agents don't work
    capsolver.api_key = capsolver_api_key
    solution = capsolver.solve(
        {
            "type": "DatadomeSliderTask",
            "websiteURL": website_url,
            "captchaUrl": captcha_url,
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",  # noqa: E501
            "proxy": proxy,
        }
    )
    return solution
