
from pathlib import Path
from argparse import ArgumentParser

import gpt_2_simple as gpt2


def generate(model_name):
    # Where to save the model
    model_dir = Path('models').joinpath(model_name)

    # Where to save Checkpoint-related stuff
    checkpoint_dir = Path('checkpoint').joinpath(model_name)

    # Load the trained model
    sess = gpt2.start_tf_sess()
    gpt2.load_gpt2(sess, checkpoint_dir=checkpoint_dir, model_dir=model_dir)

    # Generate Lyrics!
    gpt2.generate(sess, temperature=0.7, checkpoint_dir=str(checkpoint_dir), model_dir=str(model_dir))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('model_name', help='The name of the trained model. '
                                           'This should be the name of a directory under "models/"')
    args = parser.parse_args()
    generate(model_name=args.model_name)
