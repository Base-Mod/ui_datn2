-- Tạo bảng hàng đợi lệnh điều khiển
DROP TABLE IF EXISTS pending_commands;
CREATE TABLE pending_commands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slave_id INT NOT NULL UNIQUE,
    device0 INT DEFAULT 0,
    device1 INT DEFAULT 0,
    sync TINYINT(1) DEFAULT 0,  -- 1 = Cần gửi lệnh, 0 = Đã đồng bộ
    change_token TIMESTAMP NULL DEFAULT NULL, -- Dùng để nhận diện nguồn thay đổi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng lưu dữ liệu cảm biến
CREATE TABLE IF NOT EXISTS modbus_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slave_id INT NOT NULL,
    reg INT NOT NULL,
    value INT NOT NULL,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
