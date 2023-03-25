import json
import os.path
import re
from glob import glob
from typing import Any, Dict, Generator, Tuple, Union, cast
from unittest.mock import call, patch

import pytest
from _pytest.mark.structures import ParameterSet

from ethereum import rlp
from ethereum.base_types import U64
from ethereum.utils.hexadecimal import hex_to_bytes
from ethereum_spec_tools.evm_tools.fixture_loader import Load


class NoTestsFound(Exception):
    """
    An exception thrown when the test for a particular fork isn't
    available in the json fixture
    """


class NoPostState(Exception):
    """
    An exception thrown when the test does not have a postState defined.
    """


def load_test(test_case: Dict, load: Load) -> Dict:

    test_file = test_case["test_file"]
    test_key = test_case["test_key"]

    with open(test_file, "r") as fp:
        data = json.load(fp)

    json_data = data[test_key]

    blocks, block_header_hashes, block_rlps = load.json_to_blocks(
        json_data["blocks"]
    )

    try:
        raw_post_state = json_data["postState"]
    except KeyError:
        raise NoPostState
    post_state = load.json_to_state(raw_post_state)

    return {
        "test_file": test_case["test_file"],
        "test_key": test_case["test_key"],
        "genesis_header": load.json_to_header(json_data["genesisBlockHeader"]),
        "chain_id": U64(json_data["genesisBlockHeader"].get("chainId", 1)),
        "genesis_header_hash": hex_to_bytes(
            json_data["genesisBlockHeader"]["hash"]
        ),
        "genesis_block_rlp": hex_to_bytes(json_data["genesisRLP"]),
        "last_block_hash": hex_to_bytes(json_data["lastblockhash"]),
        "pre_state": load.json_to_state(json_data["pre"]),
        "expected_post_state": post_state,
        "blocks": blocks,
        "block_header_hashes": block_header_hashes,
        "block_rlps": block_rlps,
        "ignore_pow_validation": json_data["sealEngine"] == "NoProof",
    }


def run_blockchain_st_test(test_case: Dict, load: Load) -> None:

    test_data = load_test(test_case, load)

    genesis_header = test_data["genesis_header"]
    parameters = [
        genesis_header,
        (),
        (),
    ]
    if hasattr(genesis_header, "withdrawals_root"):
        parameters.append(())

    genesis_block = load.Block(*parameters)

    assert rlp.rlp_hash(genesis_header) == test_data["genesis_header_hash"]
    # FIXME: Re-enable this assertion once the genesis block RLP is
    # correctly encoded for Shanghai.
    # See https://github.com/ethereum/execution-spec-tests/issues/64
    # assert (
    #     rlp.encode(cast(rlp.RLP, genesis_block))
    #     == test_data["genesis_block_rlp"]
    # )

    chain = load.BlockChain(
        blocks=[genesis_block],
        state=test_data["pre_state"],
        chain_id=test_data["chain_id"],
    )

    if not test_data["ignore_pow_validation"] or load.proof_of_stake:
        add_blocks_to_chain(chain, test_data, load)
    else:
        with patch(
            f"ethereum.{load.fork_module}.fork.validate_proof_of_work",
            autospec=True,
        ) as mocked_pow_validator:
            add_blocks_to_chain(chain, test_data, load)
            mocked_pow_validator.assert_has_calls(
                [call(block.header) for block in test_data["blocks"]],
                any_order=False,
            )

    assert (
        rlp.rlp_hash(chain.blocks[-1].header) == test_data["last_block_hash"]
    )
    assert chain.state == test_data["expected_post_state"]
    load.close_state(chain.state)
    load.close_state(test_data["expected_post_state"])


def add_blocks_to_chain(
    chain: Any, test_data: Dict[str, Any], load: Load
) -> None:
    for idx, block in enumerate(test_data["blocks"]):
        assert (
            rlp.rlp_hash(block.header) == test_data["block_header_hashes"][idx]
        )
        assert rlp.encode(cast(rlp.RLP, block)) == test_data["block_rlps"][idx]
        load.state_transition(chain, block)


# Functions that fetch individual test cases
def load_json_fixture(test_file: str, network: str) -> Generator:
    # Extract the pure basename of the file without the path to the file.
    # Ex: Extract "world.json" from "path/to/file/world.json"
    pure_test_file = os.path.basename(test_file)
    # Extract the filename without the extension. Ex: Extract "world" from
    # "world.json"
    with open(test_file, "r") as fp:
        data = json.load(fp)

        # Search tests by looking at the `network` attribute
        found_keys = []
        for key, test in data.items():
            if "network" not in test:
                continue

            if test["network"] == network:
                found_keys.append(key)

        if not any(found_keys):
            raise NoTestsFound

        for _key in found_keys:
            yield {
                "test_file": test_file,
                "test_key": _key,
            }


def fetch_state_test_files(
    test_dir: str,
    network: str,
    only_in: Tuple[str, ...] = (),
    slow_list: Tuple[str, ...] = (),
    big_memory_list: Tuple[str, ...] = (),
    ignore_list: Tuple[str, ...] = (),
) -> Generator[Union[Dict, ParameterSet], None, None]:

    all_slow = [re.compile(x) for x in slow_list]
    all_big_memory = [re.compile(x) for x in big_memory_list]
    all_ignore = [re.compile(x) for x in ignore_list]

    # Get all the files to iterate over
    # Maybe from the custom file list or entire test_dir
    files_to_iterate = []
    if len(only_in):
        # Get file list from custom list, if one is specified
        files_to_iterate.extend(
            os.path.join(test_dir, test_path) for test_path in only_in
        )
    else:
        # If there isnt a custom list, iterate over the test_dir
        all_jsons = [
            y
            for x in os.walk(test_dir)
            for y in glob(os.path.join(x[0], "*.json"))
        ]

        files_to_iterate.extend(
            full_path
            for full_path in all_jsons
            if not any(x.search(full_path) for x in all_ignore)
        )
    # Start yielding individual test cases from the file list
    for _test_file in files_to_iterate:
        try:
            for _test_case in load_json_fixture(_test_file, network):
                # _identifier could identifiy files, folders through test_file
                #  individual cases through test_key
                _identifier = (
                    "("
                    + _test_case["test_file"]
                    + "|"
                    + _test_case["test_key"]
                    + ")"
                )
                if any(x.search(_identifier) for x in all_ignore):
                    continue
                elif any(x.search(_identifier) for x in all_slow):
                    yield pytest.param(_test_case, marks=pytest.mark.slow)
                elif any(x.search(_identifier) for x in all_big_memory):
                    yield pytest.param(_test_case, marks=pytest.mark.bigmem)
                else:
                    yield _test_case
        except NoTestsFound:
            # file doesn't contain tests for the given fork
            continue


# Test case Identifier
def idfn(test_case: Dict) -> str:
    if isinstance(test_case, dict):
        folder_name = test_case["test_file"].split("/")[-2]
        # Assign Folder name and test_key to identify tests in output
        return f"{folder_name} - " + test_case["test_key"]
