import argparse
from .config import defaults, load_config
from .data import read_data
from .engine import analyze
from .uncertainty import monte_carlo
from .export import export_results


def main():
    parser = argparse.ArgumentParser(description='MCRank 1.0 desktop / batch analysis')
    parser.add_argument('--input'); parser.add_argument('--output', default='results')
    parser.add_argument('--module', choices=['Eco', 'Human'], default='Eco')
    parser.add_argument('--mode', choices=['Auto', 'Risk', 'Screening'], default='Auto')
    parser.add_argument('--weighting', choices=['Equal', 'CRITIC', 'Custom'], default='Equal')
    parser.add_argument('--config'); parser.add_argument('--mc', action='store_true')
    args = parser.parse_args()
    if not args.input:
        from .gui import main as gui
        gui(); return
    c = load_config(args.config) if args.config else defaults()
    result = analyze(read_data(args.input), args.module, args.mode, args.weighting, c)
    if args.mc: result = monte_carlo(result)
    print(export_results(result, args.output))


if __name__ == '__main__': main()
