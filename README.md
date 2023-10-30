# Utopia Backend
To get started, install `pdm` and run `pdm install`. To run the backend, run `pdm run serve.py`

To create a table, run `pdm run python -c "import tables,utils; tables.BaseTable.metadata.create_all(utils.database)"`
