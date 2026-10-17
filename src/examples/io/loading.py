from src.persistency import load_pavement

PATH = "saved/saved_fixed.yaml"

def main():
    pavement = load_pavement(PATH)
    pavement.resolve()


main()
