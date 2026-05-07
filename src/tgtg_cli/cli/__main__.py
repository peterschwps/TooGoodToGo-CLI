from tgtg_cli.cli.app import app
from tgtg_cli.utils.version import check_for_update


def main() -> None:
    """
    Entry point of the program.
    Runs the PyPI version check and starts the Typer app with the main loop.
    """
    check_for_update()
    app()


if __name__ == "__main__":
    main()

# TODOs:
# TODO: in Docs vermerken --> dass Tools wie z.B. CleanMyMac den Cache und
#       damit auch die Login Session löschen
# TODO: nochmal Rich Optionen für Console und Live Display angucken, ist immer
#       random, wann man welche der letzten Konsoleausgaben sieht und sieht
#       nicht sauber aus
# TODO: noch bestes Delay für Monitoren rausfinden
# TODO: base.py auslagern oder als Protokoll?
