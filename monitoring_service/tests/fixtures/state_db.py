import os

import pytest

from monitoring_service.state_db import SqliteStateHandler, StateDBSqlite
from raiden_libs.utils import private_key_to_address


@pytest.fixture
def state_db_sqlite(
    get_random_address,
    server_private_key,
    monitoring_service_contract,
    tmpdir,
):
    state_db_sqlite = StateDBSqlite(os.path.join(tmpdir, 'state.sqlite3'))
    state_db_sqlite.setup_db(
        1,
        monitoring_service_contract.address,
        private_key_to_address(server_private_key),
    )
    return state_db_sqlite


@pytest.fixture
def state_handler(
    state_db_sqlite,
    custom_token,
):
    return SqliteStateHandler(state_db_sqlite.get_conn(), custom_token.address)
