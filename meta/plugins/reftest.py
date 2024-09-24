from cutekit import shell, vt100, cli, builder, model
from pathlib import Path
import re
import textwrap
import difflib
import logging

# Setup logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define color constants
WHITE = vt100.WHITE
GREEN = vt100.GREEN
RED = vt100.RED
YELLOW = vt100.YELLOW
BLUE = vt100.BLUE

def buildPaperMuncher(args: model.TargetArgs) -> builder.ProductScope:
    scope = builder.TargetScope.use(args)
    component = scope.registry.lookup("vaev-tools", model.Component)
    if component is None:
        raise RuntimeError("paper-muncher not found")
    return builder.build(scope, component)[0]

class RefTestArgs(model.TargetArgs):
    glob: str = cli.arg("g", "glob")
    fast: str = cli.arg(None, "fast", "Proceed to the next test as soon as an error occurs.")

@cli.command(None, "reftests", "Manage the reftests")
def _(args: RefTestArgs):
    paperMuncher = buildPaperMuncher(args)

    test_folder = Path(__file__).parent.parent.parent / 'tests'
    test_tmp_folder = test_folder / 'tmp'
    test_tmp_folder.mkdir(parents=True, exist_ok=True)

    temp_file = test_tmp_folder / 'reftest.xhtml'

    def update_temp_file(container, rendering):
        # Handle the case where container is None
        if container is None:
            logging.warning("Container is None. Using rendering directly.")
            xhtml = rendering
        else:
            xhtml = container.replace("<slot/>", rendering)

        with temp_file.open("w") as f:
            f.write(f"<!DOCTYPE html>\n{textwrap.dedent(xhtml)}")

    for file in test_folder.glob(args.glob or "*/*.xhtml"):
        if file.suffix != ".xhtml":
            continue
        logging.info(f"Running comparison test {file}...")

        with file.open() as f:
            content = f.read()

        Num = 0
        for id, name, test in re.findall(r"""<test\s*(?:id=['"]([^'"]+)['"])?\s*(?:name=['"]([^'"]+)['"])?\s*>([\w\W]+?)</test>""", content):
            logging.info(f"{WHITE}Test {name!r}{vt100.RESET}")
            Num += 1
            temp_file_name = re.sub(r"[^\w.-]", "_", f"{file}-{id or Num}")

            search = re.search(r"""<container>([\w\W]+?)</container>""", content)
            container = search and search.group(1)

            expected_xhtml = None
            expected_image = None
            if id:
                ref_image = file.parent / f'{id}.bmp'
                if ref_image.exists():
                    with ref_image.open('rb') as f:
                        expected_image = f.read()
                    with (test_tmp_folder / f"{temp_file_name}.expected.bmp").open("wb") as f:
                        f.write(expected_image)

            num = 0
            for tag, info, rendering in re.findall(r"""<(rendering|error)([^>]*)>([\w\W]+?)</(?:rendering|error)>""", test):
                num += 1
                if "skip" in info:
                    logging.info(f"{YELLOW}Skip test{vt100.RESET}")
                    continue

                update_temp_file(container, rendering)

                # Generate temporary BMP
                img_path = test_tmp_folder / f"{temp_file_name}-{num}.bmp"
                paperMuncher.popen("render", "-sdlpo", img_path, temp_file)
                with img_path.open('rb') as f:
                    output_image = f.read()

                # The first template is the expected value
                if not expected_xhtml:
                    expected_xhtml = rendering
                    expected_pdf = paperMuncher.popen("print", "-sdlpo", test_tmp_folder / f"{temp_file_name}.expected.pdf", temp_file)
                    if not expected_image:
                        expected_image = output_image
                        with (test_tmp_folder / f"{temp_file_name}.expected.bmp").open("wb") as f:
                            f.write(expected_image)
                        continue

                # Check if the rendering is different
                if (expected_image == output_image) == (tag == "rendering"):
                    img_path.unlink()
                    logging.info(f"{GREEN}Passed{vt100.RESET}")
                else:
                    # Generate temporary file for debugging
                    output_pdf = paperMuncher.popen("print", "-sdlpo", test_tmp_folder / f"{temp_file_name}-{num}.pdf", temp_file)

                    help_text = None
                    if " help=" in info:
                        help_match = re.search(r""" help=['"]([^'"]*)['"]""", content)
                        if help_match:
                            help_text = help_match.group(1)

                    if tag == "error":
                        logging.error(f"Failed {name!r} (The result should be different)")
                        logging.info(f"{WHITE}{expected_xhtml[1:].rstrip()}{vt100.RESET}")
                        logging.info(f"{BLUE}{rendering[1:].rstrip()}{vt100.RESET}")
                        logging.info(f"{BLUE}{test_tmp_folder / f'{temp_file_name}-{num}.pdf'}{vt100.RESET}")
                        logging.info(f"{BLUE}{test_tmp_folder / f'{temp_file_name}-{num}.bmp'}{vt100.RESET}")
                        if help_text:
                            logging.info(f"{BLUE}{help_text}{vt100.RESET}")
                    else:
                        logging.error(f"Failed {name!r}")
                        logging.info(f"{WHITE}{expected_xhtml[1:].rstrip()}{vt100.RESET}")
                        logging.info(f"{WHITE}{test_tmp_folder / f'{temp_file_name}.expected.pdf'}{vt100.RESET}")
                        logging.info(f"{WHITE}{test_tmp_folder / f'{temp_file_name}.expected.bmp'}{vt100.RESET}")
                        logging.info(f"{BLUE}{rendering[1:].rstrip()}{vt100.RESET}")
                        logging.info(f"{BLUE}{test_tmp_folder / f'{temp_file_name}-{num}.pdf'}{vt100.RESET}")
                        logging.info(f"{BLUE}{test_tmp_folder / f'{temp_file_name}-{num}.bmp'}{vt100.RESET}")
                        if help_text:
                            logging.info(f"{BLUE}{help_text}{vt100.RESET}")

                        # Print rendering diff
                        output = output_pdf.split("---")[-3]
                        expected = expected_pdf.split('---')[-3]
                        if expected == output:
                            continue
                        diff_html = []
                        theDiffs = difflib.ndiff(expected.splitlines(), output.splitlines())
                        for eachDiff in theDiffs:
                            if eachDiff[0] == "-":
                                diff_html.append(f"{RED}{eachDiff}{vt100.RESET}")
                            elif eachDiff[0] == "+":
                                diff_html.append(f"{GREEN}{eachDiff}{vt100.RESET}")
                            elif eachDiff[0] != "?":
                                diff_html.append(eachDiff)
                        logging.info('\n'.join(diff_html))

                    if args.fast:
                        break

    # Clean up temporary files
    try:
        temp_file.unlink()
    except Exception as e:
        logging.error(f"Error deleting temp file: {e}")

    # Clean up generated images
    for img in test_tmp_folder.glob(f"{temp_file_name}-*.bmp"):
        try:
            img.unlink()
        except Exception as e:
            logging.error(f"Error deleting image {img}: {e}")
