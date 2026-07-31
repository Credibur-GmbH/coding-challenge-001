The candidate is asked to implement a reconciliation process with the following ETL workflow:

1. **Extract** invoice data from a CSV file. The file path is provided in `external_resources/invoice_data.py`.
2. **Extract** bank transaction data from a mock API using the `MockBankAPI` class defined in `external_resources/mock_bank_api.py`.
3. **Transform and reconcile** the extracted data by identifying the appropriate matching criteria through data analysis.
4. **Load** the reconciliation results into a `ReconciliationReport` (defined in `external_resources/reconciliation_report.py`).

### Requirements

* The solution should be designed to scale efficiently to large datasets (e.g. 100,000+ records).
* Provide sufficient automated test coverage (both unit and integration tests) to validate the reconciliation logic.
* Implement robust error handling with clear, actionable error messages to facilitate debugging.
* The candidate is encouraged to document any assumptions made during the implementation, particularly if the matching criteria are inferred from the data rather than explicitly specified.
