CREATE TRIGGER IF NOT EXISTS auto_reset_status
BEFORE UPDATE ON pending_commands
FOR EACH ROW
BEGIN
    -- 1. Nếu giá trị thay đổi
    IF NEW.device0 <> OLD.device0 OR NEW.device1 <> OLD.device1 THEN
        -- 2. Kiểm tra xem change_token có thay đổi không?
        -- Nếu Python cập nhật: Python sẽ set change_token = NOW() -> NEW != OLD
        -- Nếu Web cập nhật: Web không đụng change_token -> NEW == OLD
        
        IF NEW.change_token <=> OLD.change_token THEN
            -- Đây là USER sửa (vì token không đổi) -> Bật cờ Sync
            SET NEW.sync = 1;
        ELSE
            -- Đây là DEVICE sửa (vì token có đổi) -> Tắt cờ Sync
            SET NEW.sync = 0;
        END IF;
    END IF;
END;
