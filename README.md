# Utopia Backend
To get started, install `pdm` and run `pdm install`. To run the backend, run `pdm run serve.py`

To create all neccessary tables, run `pdm run python -c "from utils import tables, common; tables.BaseTable.metadata.create_all(common.database)"`
