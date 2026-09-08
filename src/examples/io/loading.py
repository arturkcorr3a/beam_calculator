from src.examples.io.saving import PATH
from src.persistency import load_pavement


def main():
    pavement = load_pavement(PATH)
    pavement.resolve()
