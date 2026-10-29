-- CultureLink buyer/seller profiles. Run once on each teammate's database.
-- This script adds two tables. It preserves existing accounts and catalog data.
USE culturelinkk;

CREATE TABLE IF NOT EXISTS buyer_profiles (
    user_id INT UNSIGNED NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(40) DEFAULT NULL,
    measurement_unit VARCHAR(2) NOT NULL DEFAULT 'in',
    chest DECIMAL(6,2) UNSIGNED DEFAULT NULL,
    waist DECIMAL(6,2) UNSIGNED DEFAULT NULL,
    hips DECIMAL(6,2) UNSIGNED DEFAULT NULL,
    height DECIMAL(6,2) UNSIGNED DEFAULT NULL,
    color_preferences VARCHAR(255) DEFAULT NULL,
    culture_preferences VARCHAR(255) DEFAULT NULL,
    occasion_preferences VARCHAR(255) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_buyer_profiles_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS seller_profiles (
    user_id INT UNSIGNED NOT NULL,
    seller_id INT UNSIGNED NOT NULL,
    contact_name VARCHAR(150) NOT NULL,
    phone VARCHAR(40) DEFAULT NULL,
    cultures VARCHAR(255) NOT NULL,
    occasions VARCHAR(255) NOT NULL,
    clothing_types VARCHAR(255) NOT NULL,
    lead_time VARCHAR(150) NOT NULL,
    price_info VARCHAR(255) DEFAULT NULL,
    shipping_regions VARCHAR(255) DEFAULT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'unreviewed',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_seller_profiles_seller (seller_id),
    CONSTRAINT fk_seller_profiles_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_seller_profiles_seller FOREIGN KEY (seller_id)
        REFERENCES sellers (seller_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

SELECT 'Buyer and seller profile storage is ready' AS result;
