**Workflow Steps**
------------------

### **Step 1: Fetching Emails**

-   **Objective**: Retrieve emails from Gmail, extract metadata and HTML content, and manage processing states with labels.
-   **Logic**:
    1.  **Email Retrieval**:
        -   Fetch unread emails from specified senders using the Gmail API.
        -   Extract the following:
            -   **HTML Content**: Decode and parse the email body.
            -   **Metadata**: Extract subject, sender's email, and received date.
    2.  **Label Management**:
        -   On success:
            -   Add the label `'email fetched successfully'`.
            -   If the `'failed fetching'` label exists, remove it.
        -   On failure:
            -   Retry fetching using exponential backoff.
            -   On the **final failure attempt**:
                -   Log the failure with relevant details (e.g., email ID, sender, error message).
                -   Add the label `'failed fetching'`.
                -   Do **not save the failed HTML yet**---this will be handled in Step 3.
    3.  **Logging**:
        -   Log each attempt with timestamps, status (`SUCCESS`, `FAILURE`, or `WARNING`), and detailed messages.

* * * * *

### **Step 2: Scraping Steps**

-   **Objective**: Process the fetched email's HTML content to extract relevant information and save it to a structured format (e.g., CSV).
-   **Logic**:
    1.  **Parsing Content**:
        -   Use `BeautifulSoup` to parse the email's HTML content.
    2.  **Data Extraction**:
        -   Pass the parsed content to a scraping function to extract required data (e.g., job details).
        -   Save the extracted data to a CSV file.
    3.  **Label Management**:
        -   On success:
            -   Add the label `'successfully scraped'`.
            -   If the `'failed scraping'` label exists, remove it.
        -   On failure:
            -   Retry scraping using exponential backoff.
            -   On the **final failure attempt**:
                -   Log the failure, including the email ID, subject, and error message.
                -   Add the label `'failed scraping'`.
                -   Do **not save the failed HTML yet**---this will be handled in Step 3.
    4.  **Logging**:
        -   Log each scraping step, including successes, retries, and failures.

* * * * *

### **Step 3: Final Email Updates**

-   **Objective**: Reflect the overall processing status (success or failure) and handle file saving and logging.

#### **On Success**:

1.  Save the email content to a structured directory:
    -   **Directory Structure**:

        php

        Copy code

        `./data/<sender_name>___<sender_email>/<year>/<month>/<day>/`

    -   **File Naming**:

        php

        Copy code

        `<YYYY>_<Month>_<Day>___Time_<HH_MM_SS>___Title_<First_30_Chars>.html`

    -   **Example Path**:

        kotlin

        Copy code

        `./data/Indeed___alert@indeed.com/2024/December/21/2024_December_21___Time_15_30_00___Title_Job_Alert.html`

2.  Add a final label `'success'`.
3.  Check for a `'failure'` label:
    -   If it exists, remove it.
4.  Log the success:
    -   Include the saved file path and a summary of both steps.

#### **On Failure**:

1.  Save the email content to a structured directory **only on the final retry attempt**:
    -   **Directory Structure**:

        bash

        Copy code

        `./data/failed_emails/<sender_email>/`

    -   **File Naming**:

        php

        Copy code

        `<YYYY>_<Month>_<Day>___Time_<HH_MM_SS>___Title_<First_30_Chars>.html`

    -   **Example Path**:

        kotlin

        Copy code

        `./data/failed_emails/alert@indeed.com/2024_December_21___Time_15_30_00___Title_Job_Alert.html`

2.  Highlight failure details in logs:
    -   Specify the step that caused the failure (`Step 1: Fetching` or `Step 2: Scraping`).
    -   Include metadata about the email (e.g., subject, sender, email ID).
    -   Provide the saved file path for debugging.
3.  Add a final label `'failure'`.
4.  Log the failure:
    -   Include the error message, step responsible, and references to saved files.

* * * * *

**Logging Structure**
---------------------

1.  **Log Directory Structure**:

    -   Logs are stored in daily and monthly files for scalability and organization:

        bash

        Copy code

        `./logs/
        ├── daily/
        │   ├── 2024_December_21_log.txt
        └── monthly/
            ├── 2024_December_log.txt`

2.  **Log Entry Format**:

    -   Each log entry includes:
        -   **Timestamp**: Exact time of the event.
        -   **Step Context**: `Fetching`, `Scraping`, or `Saving`.
        -   **Status**: `SUCCESS`, `FAILURE`, or `WARNING`.
        -   **Details**: Metadata (e.g., email ID, sender, subject) or error messages.
3.  **Examples**:

    yaml

    Copy code

    `2024-12-21 15:30:00 [SUCCESS] Step: Fetching - Email fetched successfully. Sender: alert@indeed.com, Subject: Job Alert.
    2024-12-21 15:32:00 [FAILURE] Step: Scraping - Error: Missing job details in HTML. Email ID: 12345.
    2024-12-21 15:35:00 [SUCCESS] Step: Saving - Email saved to ./data/Indeed___alert@indeed.com/2024/December/21/2024_December_21___Time_15_30_00___Title_Job_Alert.html`

4.  **Retry Logs**:

    -   Log each retry attempt for visibility:

        yaml

        Copy code

        `2024-12-21 15:33:00 [WARNING] Step: Fetching - Retry 1 due to timeout.
        2024-12-21 15:34:00 [SUCCESS] Step: Fetching - Email fetched successfully after 2 retries.`

5.  **Failure Logs**:

    -   Highlight the cause of failure and reference saved HTML paths:

        vbnet

        Copy code

        `2024-12-21 15:35:00 [FAILURE] Step: Scraping - Error: Invalid HTML structure. Email ID: 12345. Path: ./data/failed_emails/alert@indeed.com/2024_December_21___Time_15_30_00___Title_Job_Alert.html`

* * * * *
