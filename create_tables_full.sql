-- =============================================
-- SQL Script tạo đầy đủ các bảng cho hệ thống
-- =============================================

-- Bảng phòng
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS energy_data;
DROP TABLE IF EXISTS pending_commands;
DROP TABLE IF EXISTS modbus_data;

CREATE TABLE rooms (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    power FLOAT DEFAULT 0,
    voltage FLOAT DEFAULT 0,
    current FLOAT DEFAULT 0,
    energy FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Bảng thiết bị
CREATE TABLE devices (
    id INT NOT NULL,
    room_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    state TINYINT(1) DEFAULT 0,
    PRIMARY KEY (id, room_id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- Bảng cài đặt
CREATE TABLE settings (
    id INT PRIMARY KEY DEFAULT 1,
    threshold_warning INT DEFAULT 500,
    threshold_critical INT DEFAULT 1000,
    tier_limit1 INT DEFAULT 50,
    tier_limit2 INT DEFAULT 100,
    tier_limit3 INT DEFAULT 200,
    tier_limit4 INT DEFAULT 300,
    tier_limit5 INT DEFAULT 400,
    tier_prices JSON,
    vat INT DEFAULT 8
);

-- Bảng dữ liệu năng lượng
CREATE TABLE energy_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    today_kwh FLOAT DEFAULT 0,
    today_cost FLOAT DEFAULT 0,
    month_kwh FLOAT DEFAULT 0,
    month_cost FLOAT DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng hàng đợi lệnh điều khiển
CREATE TABLE pending_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slave_id INT NOT NULL UNIQUE,
    device0 INT DEFAULT 0,
    device1 INT DEFAULT 0,
    sync TINYINT(1) DEFAULT 0,
    change_token TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng dữ liệu modbus
CREATE TABLE modbus_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slave_id INT NOT NULL,
    reg INT NOT NULL,
    value INT NOT NULL,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- INSERT DỮ LIỆU MẪU
-- =============================================

-- Thêm 4 phòng
INSERT INTO rooms (id, name, power, voltage, current, energy) VALUES
(1, 'Phòng 1', 862, 220.5, 3.91, 12.5),
(2, 'Phòng 2', 862, 219.8, 3.92, 10.2),
(3, 'Phòng 3', 0, 0, 0, 0),
(4, 'Phòng 4', 0, 0, 0, 0);

-- Thêm thiết bị cho mỗi phòng
INSERT INTO devices (id, room_id, name, state) VALUES
(0, 1, 'Đèn', 1),
(1, 1, 'Quạt', 1),
(0, 2, 'Đèn', 1),
(1, 2, 'Điều hòa', 1),
(0, 3, 'Đèn', 0),
(1, 3, 'Quạt', 0),
(0, 4, 'Đèn', 0),
(1, 4, 'Điều hòa', 0);

-- Thêm cài đặt mặc định
INSERT INTO settings (id, threshold_warning, threshold_critical, tier_limit1, tier_limit2, tier_limit3, tier_limit4, tier_limit5, tier_prices, vat)
VALUES (1, 502, 1000, 50, 100, 200, 300, 400, '[1984, 2050, 2380, 2998, 3350, 3460]', 8);

-- Thêm dữ liệu năng lượng mẫu
INSERT INTO energy_data (today_kwh, today_cost, month_kwh, month_cost)
VALUES (15.5, 35000, 450, 1210284);
