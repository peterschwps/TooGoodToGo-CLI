import json
from time import sleep, time

import requests

from tgtg_cli.utils.urls import shorten_url


def send_webhook(
    topic: str,
    challenge_url: str | None = None,
    header: str | None = None,
    body: str | None = None,
    actions: list[dict[str, str]] | None = None,
    seconds_to_wait: int = 240,
) -> str:
    """
    Sends a message with action buttons to the specified Ntfy.sh topic.
    The action buttons trigger a message to a newly generated response topic.
    This topic is being monitored after sending the initial message. As soon as
    the user responds to the message by clicking a button the corresponding key
    is sent to the response topic and received by this function.

    Args:
        topic (str): Topic where the user wants to receive the message
        challenge_url (str | None): Optional URL of the 3DS challenge that the
                                    user needs to open and complete.
        header (str | None): Optional header from the challengeInfoLabel if the
                             user needs to answer additional questions during
                             the 3DS challenge.
        body (str | None): Optional body from the challengeInfoText if the user
                           needs to answer additional questions during the 3DS
                           challenge.
        actions (list[dict[str, str]] | None): Optional actions if the user
                                               needs to answer additional
                                               questions during the 3DS
                                               challenge. If no value is set
                                               the default message to confirm
                                               a pending 3DS challenge is sent
                                               to the user.
                                               Defaults to None.
        seconds_to_wait (int): Seconds to wait for a response before raising an
                               exception. Defaults to 240 (4 minutes).

    Raises:
        RuntimeError: If no response was received within 10 minutes after
                      sending the message.

    Returns:
        str: Corresponding key of the selected option.
    """
    session = requests.Session()

    # End time for checking response
    endtime = round(time()) + seconds_to_wait

    # Check if additional actions are provided (meaning further steps are
    # required during the 3DS challenge)
    # Otherwise configure default message to confirm pending 3DS challenge
    if actions:
        data = {
            "topic": topic,
            "title": "Additional selection required!",
            "tags": ["hourglass_flowing_sand"],
            "message": (
                f"Please select an option from the buttons down below to "
                f"proceed with the 3DS challenge.\n\n"
                f"{header}\n"
                f"{body}\n"
            ),
            "actions": [],
        }
        for action in actions:
            key, label = list(action.items())[0]
            data["actions"].append(
                {
                    "action": "http",
                    "label": label,
                    "url": (
                        f"https://ntfy.sh/{topic}-response/publish"
                        f"?message={key}"
                    ),
                    "method": "GET",
                }
            )
    else:
        # Send message with challenge url if in-browser challenge is required
        if challenge_url:

            # Safeguard to prevent Ntfy errors if message exceeds 4KB in size
            if len(challenge_url) > 1000:
                challenge_url = shorten_url(challenge_url)

            # Send message with challenge URL
            data = {
                "topic": topic,
                "title": "In-Browser 3DS challenge!",
                "tags": ["hourglass_flowing_sand"],
                "message": (
                    "Please open the 3DS challenge by clicking the button "
                    "down below and complete all required steps."
                    "\n\n"
                    "Note: Make sure to go back to the website after "
                    "completing the challenge and wait for any redirects."
                ),
                "actions": [
                    {
                        "action": "View",
                        "label": "Challenge",
                        "url": challenge_url,
                    },
                ],
            }
            session.post(
                url="https://ntfy.sh/",
                json=data,

                timeout=30,
            )
            sleep(3)

        # Send message to confirm challenge completion
        data = {
            "topic": topic,
            "title": "Pending 3DS challenge!",
            "tags": ["hourglass_flowing_sand"],
            "message": (
                "Please accept the 3DS challenge and confirm it with the "
                "button down below."
            ) if not challenge_url else (
                "Please confirm that you have completed the 3DS challenge by "
                "clicking the button."
            ),
            "actions": [
                {
                    "action": "http",
                    "label": "Confirmed",
                    "url": (
                        f"https://ntfy.sh/{topic}-response/publish"
                        f"?message=confirmed"
                    ),
                    "method": "GET",
                }
            ],
        }

    # Send message with action button
    session.post(
        url="https://ntfy.sh/",
        json=data,
        timeout=30,
    )

    # Stream response and await confirmation
    # More details: https://docs.ntfy.sh/subscribe/api/#http-stream
    answer = None
    with session.get(
        url=f"https://ntfy.sh/{topic}-response/json",
        stream=True,
    ) as response:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                message = json.loads(line)
                event = message.get("event")
                if event == "message":
                    answer = message.get("message")
                    break
                # Note: This check only gets triggered whenever a new message
                #       is received. A keepalive message is sent every 45
                #       seconds which means that this condition might not get
                #       triggered immediately after the end time is reached.
                if endtime <= round(time()):
                    break

    # Raise exception if no response received until end time
    if answer is None:
        raise RuntimeError(
            "Notification sent but no response received in time."
        )

    # Send quick confirmation
    send_notification(
        topic=topic,
        title="Answer received!",
        message="Your answer was received.",
        headers={"tag": "grey_exclamation"},
    )
    sleep(1)  # to ensure correct order of messages when delivered

    return answer


def send_notification(
        topic: str,
        title: str,
        message: str,
        headers: dict | None = None
    ) -> None:
    """
    Sends a simple notification message to a specified Ntfy.sh topic.

    Args:
        topic (str): Topic to send the message to.
        title (str): Title of the message.
        message (str): Body of the message.
        headers (dict | None): Optional headers to include in the message.
                               Defaults to None.
    """
    requests.post(
        url="https://ntfy.sh/",
        json={
            "topic": topic,
            "title": title,
            "message": message,
        },
        headers=headers,
        timeout=30,
    )
