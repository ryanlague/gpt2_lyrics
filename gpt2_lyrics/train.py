
from pathlib import Path
from argparse import ArgumentParser

import gpt_2_simple as gpt2


def train(training_text_filepath, gpt2_model_name='124M', max_epochs=1000, sample_every=100):
    # The name of the dataset we are fine-tuning on
    dataset_name = Path(training_text_filepath).stem
    # Where to save the model
    model_dir = Path('models').joinpath(dataset_name)

    # Download the GPT-2 model (if necessary)
    # model_name is something like '124M' (see download_gpt2_model_docstring)
    if not Path("models").joinpath(gpt2_model_name).exists():
        print(f"Downloading {gpt2_model_name} model...")
        gpt2.download_gpt2(model_name=gpt2_model_name, model_dir=str(model_dir))

    # Make sure the training text exists
    if not Path(training_text_filepath).exists():
        raise Exception(f'{training_text_filepath} does not exist')

    # Where to save Checkpoint-related stuff
    checkpoint_dir = Path('checkpoint').joinpath(dataset_name)

    # Do the Training
    sess = gpt2.start_tf_sess()
    gpt2.finetune(sess, dataset=str(training_text_filepath), steps=max_epochs, sample_every=sample_every,
                  model_dir=model_dir, checkpoint_dir=str(checkpoint_dir))
    # Generate Lyrics!
    gpt2.generate(sess, temperature=0.7, checkpoint_dir=str(checkpoint_dir), model_dir=str(model_dir))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('training_text_filepath', help='Path to .txt file containing training text')
    parser.add_argument('-max_epochs', type=int, default=500,
                        help='Stop after at most this many epochs have been completed (or the model has converged)')
    args = parser.parse_args()
    train(training_text_filepath=args.training_text_filepath, gpt2_model_name='124M', max_epochs=args.max_epochs)
