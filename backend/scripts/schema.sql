-- SolarSaathi database. Run with scripts\init_db.py (safe to run again: blocks only create what is missing).
-- Blocks are separated by a blank line.

IF OBJECT_ID('Users') IS NULL
CREATE TABLE Users (
    user_id         INT IDENTITY PRIMARY KEY,
    full_name       NVARCHAR(100) NOT NULL,
    email           NVARCHAR(150) NOT NULL UNIQUE,
    password_hash   NVARCHAR(200) NOT NULL,
    role            NVARCHAR(20)  NOT NULL CONSTRAINT CK_Users_role CHECK (role IN ('admin', 'sales')),
    is_active       BIT NOT NULL DEFAULT 1,
    failed_logins   INT NOT NULL DEFAULT 0,
    locked_until    DATETIME2 NULL,
    last_login      DATETIME2 NULL,
    token_version   INT NOT NULL DEFAULT 0,
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

-- One chat = one session. Customers do not log in; the browser keeps the random session_id.
IF OBJECT_ID('ChatSessions') IS NULL
CREATE TABLE ChatSessions (
    session_id      CHAR(32) PRIMARY KEY,
    channel         NVARCHAR(20) NOT NULL DEFAULT 'web',
    bill_data       NVARCHAR(MAX) NULL,          -- JSON read from the bill photo (no name / address)
    latest_quote_id INT NULL,
    turns           INT NOT NULL DEFAULT 0,
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    last_active     DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

IF OBJECT_ID('ChatMessages') IS NULL
CREATE TABLE ChatMessages (
    message_id      BIGINT IDENTITY PRIMARY KEY,
    session_id      CHAR(32) NOT NULL REFERENCES ChatSessions(session_id),
    role            NVARCHAR(10) NOT NULL CONSTRAINT CK_Msg_role CHECK (role IN ('user', 'assistant', 'event')),
    content         NVARCHAR(MAX) NOT NULL,
    model           NVARCHAR(80) NULL,           -- which AI answered (Groq or the Gemini backup)
    tools_used      NVARCHAR(400) NULL,
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ChatMessages_session')
CREATE INDEX IX_ChatMessages_session ON ChatMessages(session_id, message_id)

-- Every calculation the agent (or the quick calculator) makes. public_token = the shareable link.
IF OBJECT_ID('Quotes') IS NULL
CREATE TABLE Quotes (
    quote_id        INT IDENTITY PRIMARY KEY,
    session_id      CHAR(32) NULL REFERENCES ChatSessions(session_id),
    public_token    CHAR(32) NOT NULL UNIQUE,
    city            NVARCHAR(40) NOT NULL,
    average_units   INT NOT NULL,
    recommended     NVARCHAR(10) NOT NULL,
    recommended_kw  DECIMAL(6, 2) NOT NULL,
    recommended_cost INT NOT NULL,
    result_json     NVARCHAR(MAX) NOT NULL,
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

-- A customer who agreed to be contacted.
IF OBJECT_ID('Leads') IS NULL
CREATE TABLE Leads (
    lead_id         INT IDENTITY PRIMARY KEY,
    session_id      CHAR(32) NULL REFERENCES ChatSessions(session_id),
    quote_id        INT NULL REFERENCES Quotes(quote_id),
    customer_name   NVARCHAR(100) NOT NULL,
    phone           NVARCHAR(20) NOT NULL,
    city            NVARCHAR(40) NULL,
    preferred_option NVARCHAR(10) NULL,
    status          NVARCHAR(12) NOT NULL DEFAULT 'new'
                    CONSTRAINT CK_Leads_status CHECK (status IN ('new', 'contacted', 'site_visit', 'won', 'lost')),
    notes           NVARCHAR(1000) NULL,
    updated_by      INT NULL REFERENCES Users(user_id),
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    updated_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

IF OBJECT_ID('Prices') IS NULL
CREATE TABLE Prices (
    price_key       NVARCHAR(40) PRIMARY KEY,
    value           DECIMAL(12, 2) NOT NULL,
    updated_by      INT NULL REFERENCES Users(user_id),
    updated_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

IF OBJECT_ID('AuditLog') IS NULL
CREATE TABLE AuditLog (
    audit_id        BIGINT IDENTITY PRIMARY KEY,
    user_id         INT NULL,
    action          NVARCHAR(40) NOT NULL,
    target          NVARCHAR(100) NULL,
    details         NVARCHAR(400) NULL,
    ip_address      NVARCHAR(45) NULL,
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)

-- ===== Version 2 =====
-- Where the customer is (only if they press "use my location"): better sunlight data. Rounded, no address.
IF COL_LENGTH('ChatSessions', 'location') IS NULL
ALTER TABLE ChatSessions ADD location NVARCHAR(40) NULL

-- "Book a free site survey"
IF OBJECT_ID('SurveyBookings') IS NULL
CREATE TABLE SurveyBookings (
    booking_id      INT IDENTITY PRIMARY KEY,
    session_id      CHAR(32) NULL REFERENCES ChatSessions(session_id),
    quote_id        INT NULL REFERENCES Quotes(quote_id),
    customer_name   NVARCHAR(100) NOT NULL,
    phone           NVARCHAR(20) NOT NULL,
    area            NVARCHAR(120) NOT NULL,      -- sector / town only, e.g. "G-11, Islamabad"
    preferred_date  DATE NOT NULL,
    time_slot       NVARCHAR(10) NOT NULL CONSTRAINT CK_Survey_slot CHECK (time_slot IN ('morning', 'afternoon', 'evening')),
    status          NVARCHAR(10) NOT NULL DEFAULT 'requested'
                    CONSTRAINT CK_Survey_status CHECK (status IN ('requested', 'confirmed', 'done', 'cancelled')),
    notes           NVARCHAR(1000) NULL,
    updated_by      INT NULL REFERENCES Users(user_id),
    created_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    updated_at      DATETIME2 NOT NULL DEFAULT SYSDATETIME()
)
