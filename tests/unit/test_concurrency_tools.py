
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from app.ai.tools.chatTools import extract_data, python_inter, extracted_dataframes
from app.db.session import engine

# Mock engine to return different data based on query
def mock_read_sql(query, con):
    if "user_thread_A" in query:
        return pd.DataFrame({"id": [1], "val": ["A"]})
    elif "user_thread_B" in query:
        return pd.DataFrame({"id": [2], "val": ["B"]})
    return pd.DataFrame()

@pytest.fixture
def clean_extracted_dataframes():
    extracted_dataframes.clear()
    yield
    extracted_dataframes.clear()

@patch("pandas.read_sql", side_effect=mock_read_sql)
def test_concurrency_isolation(mock_read, clean_extracted_dataframes):
    # Simulate Thread A extracting data "my_df"
    config_a = {"configurable": {"thread_id": "thread_A"}}
    # extract_data is a StructuredTool, invoke it properly
    extract_data.invoke({"sql_query": "SELECT * FROM user_thread_A", "df_name": "my_df"}, config=config_a)
    
    # Simulate Thread B extracting data "my_df" (same name!)
    config_b = {"configurable": {"thread_id": "thread_B"}}
    extract_data.invoke({"sql_query": "SELECT * FROM user_thread_B", "df_name": "my_df"}, config=config_b)
    
    # Verify isolation in extracted_dataframes
    assert "thread_A" in extracted_dataframes
    assert "thread_B" in extracted_dataframes
    assert extracted_dataframes["thread_A"]["my_df"].iloc[0]["val"] == "A"
    assert extracted_dataframes["thread_B"]["my_df"].iloc[0]["val"] == "B"
    
    # Verify python_inter context isolation
    # Thread A should see "A"
    res_a = python_inter.invoke({"py_code": "my_df.iloc[0]['val']"}, config=config_a)
    assert "A" in res_a
    
    # Thread B should see "B"
    res_b = python_inter.invoke({"py_code": "my_df.iloc[0]['val']"}, config=config_b)
    assert "B" in res_b

