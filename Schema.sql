-- ============================================================
--  SplitX Database Schema — MySQL (Fully Normalized to 3NF)
--  Version 2.0 — Normalization + Bug Fixes Applied
-- ============================================================
--
--  NORMALIZATION FIXES APPLIED:
--  1NF — No repeating groups; atomic columns (name split into first/last)
--  2NF — No partial dependencies; split_type moved from splits → expenses
--  3NF — No transitive dependencies; ENUMs replaced with lookup tables
--         (currencies, group_categories, expense_categories, split_types,
--          payment_statuses, member_roles) so values are extensible without
--          ALTER TABLE
--
--  OTHER BUGS FIXED:
--  • split_type was on splits (wrong) — it belongs on expenses (one type per expense)
--  • currency duplicated across expenses + payments → now FK to currencies table
--  • No link between payments and which splits they settle → split_settlements added
--  • splits missing updated_at (is_settled changes over time)
--  • users.name was a multi-value field → split into first_name + last_name
--  • groups.category and expenses.category were different ENUMs → separate lookup tables
-- ============================================================

CREATE DATABASE IF NOT EXISTS splitx
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE splitx;

-- ============================================================
-- LOOKUP TABLES  (reference / domain tables)
-- These replace all ENUM columns for proper 3NF.
-- ============================================================

-- 1a. Currencies  (ISO 4217)
CREATE TABLE currencies (
    code        CHAR(3)      NOT NULL,   -- e.g. PKR, USD, EUR
    name        VARCHAR(60)  NOT NULL,   -- e.g. Pakistani Rupee
    symbol      VARCHAR(10)  NOT NULL,   -- e.g. ₨, $, €

    PRIMARY KEY (code)
);

INSERT INTO currencies (code, name, symbol) VALUES
    ('PKR', 'Pakistani Rupee',  '₨'),
    ('USD', 'US Dollar',        '$'),
    ('EUR', 'Euro',             '€'),
    ('GBP', 'British Pound',    '£'),
    ('AED', 'UAE Dirham',       'د.إ');

-- ------------------------------------------------------------
-- 1b. Group categories
CREATE TABLE group_categories (
    id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(50)      NOT NULL UNIQUE,  -- trip, home, food, work, other …

    PRIMARY KEY (id)
);

INSERT INTO group_categories (name) VALUES
    ('trip'), ('home'), ('food'), ('work'), ('other');

-- ------------------------------------------------------------
-- 1c. Expense categories
CREATE TABLE expense_categories (
    id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(50)      NOT NULL UNIQUE,

    PRIMARY KEY (id)
);

INSERT INTO expense_categories (name) VALUES
    ('food'), ('transport'), ('accommodation'),
    ('entertainment'), ('shopping'), ('utilities'), ('other');

-- ------------------------------------------------------------
-- 1d. Split types
CREATE TABLE split_types (
    id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(30)      NOT NULL UNIQUE,  -- equal, exact, percentage

    PRIMARY KEY (id)
);

INSERT INTO split_types (name) VALUES
    ('equal'), ('exact'), ('percentage');

-- ------------------------------------------------------------
-- 1e. Payment statuses
CREATE TABLE payment_statuses (
    id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(30)      NOT NULL UNIQUE,  -- pending, completed, cancelled

    PRIMARY KEY (id)
);

INSERT INTO payment_statuses (name) VALUES
    ('pending'), ('completed'), ('cancelled');

-- ------------------------------------------------------------
-- 1f. Member roles
CREATE TABLE member_roles (
    id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(30)      NOT NULL UNIQUE,  -- admin, member

    PRIMARY KEY (id)
);

INSERT INTO member_roles (name) VALUES
    ('admin'), ('member');

-- ============================================================
-- CORE TABLES
-- ============================================================

-- 2. USERS
--    1NF fix: name → first_name + last_name (atomic columns)
-- ============================================================
CREATE TABLE users (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    first_name    VARCHAR(60)   NOT NULL,
    last_name     VARCHAR(60)   NOT NULL,
    email         VARCHAR(150)  NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    phone         VARCHAR(20)   DEFAULT NULL,
    avatar_url    VARCHAR(500)  DEFAULT NULL,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    INDEX idx_users_phone (phone)
);

-- ============================================================
-- 3. GROUPS
--    category_id → FK to group_categories (replaces ENUM)
-- ============================================================
CREATE TABLE `groups` (
    id           INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name         VARCHAR(150)    NOT NULL,
    description  VARCHAR(500)    DEFAULT NULL,
    category_id  TINYINT UNSIGNED NOT NULL DEFAULT 5,  -- 5 = 'other'
    created_by   INT UNSIGNED    NOT NULL,
    created_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_groups_created_by (created_by),

    CONSTRAINT fk_groups_category
        FOREIGN KEY (category_id) REFERENCES group_categories (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_groups_created_by
        FOREIGN KEY (created_by) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================
-- 4. GROUP_MEMBERS
--    role_id → FK to member_roles (replaces ENUM)
-- ============================================================
CREATE TABLE group_members (
    id        INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    group_id  INT UNSIGNED    NOT NULL,
    user_id   INT UNSIGNED    NOT NULL,
    role_id   TINYINT UNSIGNED NOT NULL DEFAULT 2,     -- 2 = 'member'
    joined_at TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_group_user (group_id, user_id),      -- one membership per user per group
    INDEX idx_gm_user (user_id),

    CONSTRAINT fk_gm_group
        FOREIGN KEY (group_id) REFERENCES `groups` (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_gm_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_gm_role
        FOREIGN KEY (role_id) REFERENCES member_roles (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================
-- 5. EXPENSES
--    2NF fix: split_type_id moved HERE from splits table
--             (the split method is a property of the expense,
--              not of each individual split row)
--    3NF fix: currency_code → FK to currencies
--             category_id   → FK to expense_categories
-- ============================================================
CREATE TABLE expenses (
    id              INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    group_id        INT UNSIGNED     NOT NULL,
    paid_by         INT UNSIGNED     NOT NULL,          -- user who paid upfront
    title           VARCHAR(200)     NOT NULL,
    description     TEXT             DEFAULT NULL,
    amount          DECIMAL(12, 2)   NOT NULL,          -- total expense amount
    currency_code   CHAR(3)          NOT NULL DEFAULT 'PKR',
    category_id     TINYINT UNSIGNED NOT NULL DEFAULT 7,  -- 7 = 'other'
    split_type_id   TINYINT UNSIGNED NOT NULL DEFAULT 1,  -- 1 = 'equal'
    expense_date    DATE             NOT NULL,
    created_at      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                              ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_exp_group   (group_id),
    INDEX idx_exp_paid_by (paid_by),
    INDEX idx_exp_date    (expense_date),

    CONSTRAINT fk_exp_group
        FOREIGN KEY (group_id) REFERENCES `groups` (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_exp_paid_by
        FOREIGN KEY (paid_by) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_exp_currency
        FOREIGN KEY (currency_code) REFERENCES currencies (code)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_exp_category
        FOREIGN KEY (category_id) REFERENCES expense_categories (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_exp_split_type
        FOREIGN KEY (split_type_id) REFERENCES split_types (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT chk_expense_amount CHECK (amount > 0)
);

-- ============================================================
-- 6. SPLITS  (each user's share of an expense)
--    split_type removed (now on expenses — 2NF fix)
--    updated_at added (is_settled changes over time)
-- ============================================================
CREATE TABLE splits (
    id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    expense_id  INT UNSIGNED   NOT NULL,
    user_id     INT UNSIGNED   NOT NULL,               -- user who owes this share
    owed_amount DECIMAL(12, 2) NOT NULL,               -- exact amount owed
    is_settled  TINYINT(1)     NOT NULL DEFAULT 0,     -- 0 = outstanding, 1 = fully settled
    created_at  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_split_expense_user (expense_id, user_id),  -- one share per user per expense
    INDEX idx_splits_user      (user_id),
    INDEX idx_splits_settled   (is_settled),

    CONSTRAINT fk_split_expense
        FOREIGN KEY (expense_id) REFERENCES expenses (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_split_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT chk_owed_amount CHECK (owed_amount >= 0)
);

-- ============================================================
-- 7. PAYMENTS  (direct money transfers between users)
--    3NF fix: currency_code → FK to currencies
--             status_id     → FK to payment_statuses
-- ============================================================
CREATE TABLE payments (
    id            INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    group_id      INT UNSIGNED     NOT NULL,
    payer_id      INT UNSIGNED     NOT NULL,            -- user sending money
    payee_id      INT UNSIGNED     NOT NULL,            -- user receiving money
    amount        DECIMAL(12, 2)   NOT NULL,
    currency_code CHAR(3)          NOT NULL DEFAULT 'PKR',
    status_id     TINYINT UNSIGNED NOT NULL DEFAULT 1,  -- 1 = 'pending'
    note          VARCHAR(300)     DEFAULT NULL,
    paid_at       TIMESTAMP        DEFAULT NULL,        -- set when status → completed
    created_at    TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_pay_group  (group_id),
    INDEX idx_pay_payer  (payer_id),
    INDEX idx_pay_payee  (payee_id),
    INDEX idx_pay_status (status_id),

    CONSTRAINT fk_pay_group
        FOREIGN KEY (group_id) REFERENCES `groups` (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_pay_payer
        FOREIGN KEY (payer_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT fk_pay_payee
        FOREIGN KEY (payee_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT fk_pay_currency
        FOREIGN KEY (currency_code) REFERENCES currencies (code)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_pay_status
        FOREIGN KEY (status_id) REFERENCES payment_statuses (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    CONSTRAINT chk_payer_ne_payee CHECK (payer_id <> payee_id)
);

-- ============================================================
-- 8. SPLIT_SETTLEMENTS  (bridge: links payments → splits they settle)
--    NEW TABLE — fixes the missing audit trail between payments
--    and which specific splits got settled by that payment.
--    A single payment can partially or fully settle one or more splits.
-- ============================================================
CREATE TABLE split_settlements (
    id               INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    payment_id       INT UNSIGNED   NOT NULL,
    split_id         INT UNSIGNED   NOT NULL,
    settled_amount   DECIMAL(12, 2) NOT NULL,          -- portion of this split covered by this payment

    PRIMARY KEY (id),
    UNIQUE KEY uq_settlement (payment_id, split_id),   -- one entry per payment-split pair

    CONSTRAINT fk_ss_payment
        FOREIGN KEY (payment_id) REFERENCES payments (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_ss_split
        FOREIGN KEY (split_id) REFERENCES splits (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT chk_settled_amount CHECK (settled_amount > 0)
);

-- ============================================================
-- END OF SCHEMA
-- ============================================================