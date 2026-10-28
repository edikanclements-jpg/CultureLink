USE culturelinkk;
-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 15, 2026 at 11:17 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `culturelinkk`
--

-- --------------------------------------------------------

--
-- Table structure for table `comparisonselections`
--

CREATE TABLE `comparisonselections` (
  `comparison_id` int(10) UNSIGNED NOT NULL,
  `session_id` varchar(255) NOT NULL,
  `item_id` int(10) UNSIGNED NOT NULL,
  `date_added` datetime NOT NULL DEFAULT current_timestamp(),
  `expires_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cultures`
--

CREATE TABLE `cultures` (
  `culture_id` int(10) UNSIGNED NOT NULL,
  `culture_name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `cultures`
--

INSERT INTO `cultures` (`culture_id`, `culture_name`) VALUES
(1, 'Indian'),
(2, 'Nigerian');

-- --------------------------------------------------------

--
-- Table structure for table `itemoccasions`
--

CREATE TABLE `itemoccasions` (
  `item_id` int(10) UNSIGNED NOT NULL,
  `occasion_id` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `itemoccasions`
--

INSERT INTO `itemoccasions` (`item_id`, `occasion_id`) VALUES
(1, 2),
(2, 2),
(3, 2),
(4, 3),
(5, 1),
(8, 2),
(9, 2),
(10, 2),
(11, 2),
(12, 2),
(13, 1),
(14, 1),
(15, 1),
(16, 1),
(17, 1),
(18, 1),
(19, 2),
(43, 1),
(43, 3),
(44, 1),
(44, 3),
(45, 1),
(45, 3),
(46, 1),
(46, 3),
(47, 1),
(47, 3),
(48, 1),
(48, 3),
(49, 1),
(49, 3),
(50, 1),
(50, 3),
(51, 1),
(51, 3);

-- --------------------------------------------------------

--
-- Table structure for table `items`
--

CREATE TABLE `items` (
  `item_id` int(10) UNSIGNED NOT NULL,
  `seller_id` int(10) UNSIGNED NOT NULL,
  `culture_id` int(10) UNSIGNED NOT NULL,
  `item_name` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `category` varchar(100) NOT NULL,
  `price` decimal(10,2) UNSIGNED NOT NULL,
  `image_url` varchar(255) DEFAULT NULL,
  `purchase_url` varchar(255) DEFAULT NULL,
  `price_notes` text DEFAULT NULL,
  `last_verified_at` datetime DEFAULT NULL,
  `color` varchar(100) DEFAULT NULL,
  `size` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `items`
--

INSERT INTO `items` (`item_id`, `seller_id`, `culture_id`, `item_name`, `description`, `category`, `price`, `image_url`, `purchase_url`, `price_notes`, `last_verified_at`, `color`, `size`) VALUES
(1, 1, 1, 'Evani Kurta Set - Beige', 'Beige kurta set; style S26RD10 (details unverified).', 'Kurta Set', 380.00, 'https://us.anitadongre.com/dw/image/v2/BGCX_PRD/on/demandware.static/-/Sites-masterCatalog_AD_India/default/dw38d06bcc/images/hires/F25/Women/S26RD10_Beige_1.jpg?sh=300&sm=fit&strip=false&sw=200', 'https://us.anitadongre.com/women/clothing/kurta-sets?page=2', 'Demonstration price in USD from earlier working list; not independently verified. Purchase link is category page.', NULL, 'Beige', 'XS, S, M, L, XL, XXL'),
(2, 1, 1, 'Flori Kurta Set - Blue', 'Blue kurta set; style S26AY3 (details unverified).', 'Kurta Set', 430.00, 'https://us.anitadongre.com/dw/image/v2/BGCX_PRD/on/demandware.static/-/Sites-masterCatalog_AD_India/default/dw6f167da2/images/hires/F25/Women/S26AY3_BLUE_1.jpg?sh=300&sm=fit&strip=false&sw=200', 'https://us.anitadongre.com/women/clothing/kurta-sets?page=2', 'Demonstration price in USD from earlier working list; not independently verified. Purchase link is category page.', NULL, 'Blue', 'XS, S, M, L, XL'),
(3, 1, 1, 'Shaima Kurta Set - Yellow', 'Yellow kurta set; style S26AS16 (details unverified).', 'Kurta Set', 380.00, 'https://us.anitadongre.com/dw/image/v2/BGCX_PRD/on/demandware.static/-/Sites-masterCatalog_AD_India/default/dwcb2193e3/images/hires/F25/Women/S26AS16_Yellow_1.jpg?sh=300&sm=fit&strip=false&sw=200', 'https://us.anitadongre.com/women/clothing/kurta-sets?page=2', 'Demonstration price in USD from earlier working list; not independently verified. Purchase link is category page.', NULL, 'Yellow', 'XS, S, M, L, XL, XXL'),
(4, 1, 1, 'Alishba Kurta Set - Black', 'Black kurta set; style F25RN26 (details unverified).', 'Kurta Set', 400.00, 'https://us.anitadongre.com/dw/image/v2/BGCX_PRD/on/demandware.static/-/Sites-masterCatalog_AD_India/default/dwd889a021/images/hires/F25/Women/F25RN26_Black_1.jpg?sh=300&sm=fit&strip=false&sw=200', 'https://us.anitadongre.com/women/clothing/kurta-sets?page=2', 'Demonstration price in USD from earlier working list; not independently verified. Purchase link is category page.', NULL, 'Black', 'XS, S, M, L'),
(5, 1, 1, 'Misbah Kurta Set - Yellow', 'Yellow kurta set; style S26AY10 (details unverified).', 'Kurta Set', 610.00, 'https://us.anitadongre.com/dw/image/v2/BGCX_PRD/on/demandware.static/-/Sites-masterCatalog_AD_India/default/dw098d37a6/images/hires/F25/Women/S26AY10_Yellow_1.jpg?sh=300&sm=fit&strip=false&sw=200', 'https://us.anitadongre.com/women/clothing/kurta-sets?page=2', 'Demonstration price in USD from earlier working list; not independently verified. Purchase link is category page.', NULL, 'Yellow', 'XS, S, M, L, XL, XXL'),
(8, 2, 1, 'Light Orange Kurta & Pant Set in Rayon silk', 'Rayon silk kurta and pant set.', 'Kurta Set', 54.00, 'https://www.anuattires.com/cdn/shop/files/14_front_StandingElegantly_1000x.jpg?v=1768767435', 'https://www.anuattires.com/collections/kurta-pant-sets', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Light Orange', 'Custom Sizes'),
(9, 2, 1, 'Green Kurta & Pant Set in Gajji Silk', 'Gajji silk kurta and pant set.', 'Kurta Set', 86.00, 'https://www.anuattires.com/cdn/shop/files/sea_green-_earthy_shade-gajji_silk_1300x.heic?v=1764444899', 'https://www.anuattires.com/collections/kurta-pant-sets', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Green', 'Custom Sizes'),
(10, 2, 1, 'Wine Kurta & Pant Set in Gajji Silk', 'Gajji silk kurta and pant set.', 'Kurta Set', 86.00, 'https://www.anuattires.com/cdn/shop/files/Copy_of_Copy_of_Copy_of_IMG_1199_model_front_1300x.png?v=1764271363', 'https://www.anuattires.com/collections/kurta-pant-sets', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Wine', 'Custom Sizes'),
(11, 2, 1, 'Pista Green Kurta & Pant Set', 'Kurta and pant set.', 'Kurta Set', 68.00, 'https://www.anuattires.com/cdn/shop/files/27_front_StandingElegantly_1300x.jpg?v=1768771069', 'https://www.anuattires.com/collections/kurta-pant-sets', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Pista Green', 'Custom Sizes'),
(12, 2, 1, 'Red Straight Cut Kurta', 'Straight cut kurta.', 'Kurta', 38.00, 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT0ditt4kVPmYkqoD-uLLiUjn11xuHUMLMx_c9nbGhTUA&s=10', 'https://www.anuattires.com/collections/straightcut-kurtas', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Red', 'Custom Sizes'),
(13, 2, 1, 'Gold Floral Lehenga', 'Floral lehenga.', 'Lehenga', 360.00, 'https://www.anuattires.com/cdn/shop/files/5_492e610a-1bb6-4306-91a5-15e0ad63e513_1300x.png?v=1763585194', 'https://www.anuattires.com/collections/designer-indian-wedding-lehengas', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Gold', 'Custom Sizes'),
(14, 2, 1, 'Bottle Green Banaras Lehenga', 'Banaras lehenga.', 'Lehenga', 230.00, 'https://www.anuattires.com/cdn/shop/files/Anuhs75_1300x.jpg?v=1757794694', 'https://www.anuattires.com/collections/designer-indian-wedding-lehengas', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Bottle Green', 'Custom Sizes'),
(15, 2, 1, 'Baby Pink Chiffon Lehenga', 'Chiffon lehenga; shown sold out when reviewed.', 'Lehenga', 590.00, 'https://www.anuattires.com/cdn/shop/files/2_front_Standing_Elegantly_1_1300x.jpg?v=1770235440', 'https://www.anuattires.com/collections/designer-indian-wedding-lehengas', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Baby Pink', 'Custom Sizes'),
(16, 2, 1, 'Lavender Pure Banaras Saree', 'Banaras saree.', 'Saree', 645.00, 'https://www.anuattires.com/cdn/shop/files/CAON9845_1_1300x.jpg?v=1778962347', 'https://www.anuattires.com/collections/traditional-indian-sarees', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Lavender', 'Custom Sizes'),
(17, 2, 1, 'Red Patan Patola Saree', 'Patan Patola saree.', 'Saree', 330.00, 'https://www.anuattires.com/cdn/shop/files/CAON9977_1300x.jpg?v=1778963741', 'https://www.anuattires.com/collections/traditional-indian-sarees', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Red', 'Custom Sizes'),
(18, 2, 1, 'Blue & Red Dola Silk Half Saree', 'Dola silk half saree.', 'Half Saree', 222.00, 'https://www.anuattires.com/cdn/shop/files/Gemini_Generated_Image_u5b07iu5b07iu5b0_1300x.png?v=1786301654', 'https://www.anuattires.com/collections/traditional-half-sarees', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Blue, Red', 'Custom Sizes'),
(19, 2, 1, 'Black Chinnon Anarkali Set', 'Chinnon Anarkali set.', 'Anarkali', 150.00, 'https://www.anuattires.com/cdn/shop/files/Gemini_Generated_Image_bf59aqbf59aqbf59_1300x.png?v=1777145620', 'https://www.anuattires.com/collections/all', 'USD listing price checked 2026-10-13; verify before buying. Sizes not individually verified; demonstration listing.', NULL, 'Black', 'Custom Sizes'),
(38, 5, 1, 'Kashida Pattu Straight Dress - Ivory & Blue Stripes', 'Handwoven cotton straight dress; calf or ankle length options. Product code NDK01A.', 'Dress', 3380.00, 'https://theindiacrafthouse.com/cdn/shop/files/The_20Work_20Edit._20Handwoven_20Kashida_20Pattu_20Straight_20Dress_20-_20Ivory_20_26_20Blue_20Stripes_20-_20NDK01A_203.jpg?v=1756751296', 'https://theindiacrafthouse.com/en-us/products/the-work-edit-handwoven-kashida-pattu-straight-dress-ivory-blue-stripes-ndk01a', 'INR 3380 listed on retailer site; NOT USD. Verify price and availability before publishing.', NULL, 'Off-White, Blue', 'XS, S, M, L, XL, XXL'),
(39, 5, 1, 'Bagru Printed Dress - Rhombus Trail', 'Hand block-printed cotton midi dress. Product code NDBPDC01A.', 'Dress', 2880.00, 'https://theindiacrafthouse.com/cdn/shop/files/The_20Work_20Edit._20Bagru_20HandBlock_20Printed_20Dress_20-_20Rhombus_20Trail_20-_20NDBPDC01A_203.jpg?v=1757348633', 'https://theindiacrafthouse.com/en-us/products/the-work-edit-bagru-handblock-printed-dress-rhombus-trail-ndbpdc01a', 'INR 2880 listed on retailer site; NOT USD. Verify price and availability before publishing.', NULL, 'Rust Red, Indigo, Black', 'XS, S, M, L, XL, XXL'),
(40, 5, 1, 'Kashida Pattu Wrap Skirt & Top - Green Aztec', 'Handwoven cotton wrap skirt and coordinated top; portfolio listing was marked sold out when checked. Product code NTWUM01C.', 'Skirt & Top Set', 3090.00, 'https://theindiacrafthouse.com/cdn/shop/files/The_20Work_20Edit._20Handwoven_20Kashida_20Pattu_20Cotton_20Wrap_20Skirt_20_26_20Top_20Set_20-_20Teal_20Aztec_20_28Set_20of_202_29_20-_20NTWUM01C_203.jpg?v=1756751592', 'https://theindiacrafthouse.com/en-us/products/the-work-edit-handwoven-kashida-pattu-cotton-wrap-skirt-top-set-green-aztec-set-of-2-ntwum01c', 'INR 3090 listed on retailer site; NOT USD. Product marked SOLD OUT when checked.', NULL, 'Green, Off-White', 'XS, S, M, L, XL, XXL'),
(41, 5, 1, 'Khadi Cotton Dress - Mint Horizon', 'Handwoven khadi cotton dress with calf and ankle length options. Product code NDSMH01B.', 'Dress', 2580.00, 'https://theindiacrafthouse.com/cdn/shop/files/Handwoven_20Khadi_20Cotton_20Dress_20-_20Mint_20Horizon_20-_20NDSMH01B.jpg?v=1756751859', 'https://theindiacrafthouse.com/en-us/products/handwoven-khadi-cotton-dress-mint-horizon-ndsmh01b', 'INR 2580 listed on retailer site; NOT USD. Verify price and availability before publishing.', NULL, 'Mint Green, Off-White', 'XS, S, M, L, XL, XXL'),
(42, 5, 1, 'Bagru Kota Doria Saree - Ivory Fern', 'Hand block-printed saree, approximately 6 meters long. Product code NINS02P.', 'Saree', 3020.00, 'https://theindiacrafthouse.com/cdn/shop/files/NINS02P_201_281_29.jpg?v=1791485321', 'https://theindiacrafthouse.com/products/bagru-statements-hand-block-printed-kota-doria-saree-ivory-fern-nins02p', 'INR 3020 listed on retailer site; NOT USD. Verify price and availability before publishing.', NULL, 'Beige, Black, Blue, Gold', 'One Size (6 m saree)'),
(43, 6, 2, 'Klothouse Royal Blue Beaded Dress', 'Royal blue fitted gown with an off-the-shoulder sweetheart neckline, sheer long sleeves, and a structured bodice. Ornate beadwork and sequin patterns continue down the long skirt.', 'Dress', 0.00, 'Nigerian Dresses/Klothouse - Blue Dress.png', NULL, 'To be determined', NULL, 'Royal Blue', 'To be measured'),
(44, 6, 2, 'Klothouse Orange Sculpted Gown', 'Bright orange gown with a fitted, embellished bodice and an asymmetric neckline. Large pleated ruffles curl around the shoulders and skirt, framing a high front slit and a trailing hem.', 'Dress', 0.00, 'Nigerian Dresses/Klothouse Orange Dress.png', NULL, 'To be determined', NULL, 'Orange, Silver', 'To be measured'),
(45, 6, 2, 'Klothouse Red Draped Dress', 'Red off-the-shoulder gown with a densely embellished bodice and a draped skirt. A large rosette detail sits at the hip, with green vine embroidery down the front.', 'Dress', 0.00, 'Nigerian Dresses/Klothouse Red Dress.png', NULL, 'To be determined', NULL, 'Red, Green', 'To be measured'),
(46, 7, 2, 'Olis Collections Blue Beaded Gown', 'Blue gown with a sweetheart neckline, halter straps, sheer long sleeves, and a pointed fitted bodice. Beaded and sequined patterns decorate the long skirt, with a gathered drape falling from the waist.', 'Dress', 0.00, 'Nigerian Dresses/Olis Collections - Blue Dres.png', NULL, 'To be determined', NULL, 'Royal Blue, Light Blue, Silver', 'To be measured'),
(47, 7, 2, 'Olis Collections Pink Leaf-Detail Mermaid Gown', 'Pink mermaid gown with sculpted leaf-shaped decorations across the off-the-shoulder neckline. Sparkling beadwork, hanging bead fringe at the upper arms, and a flared skirt with a train complete the design.', 'Dress', 0.00, 'Nigerian Dresses/Olis Collections - Pink Dress.png', NULL, 'To be determined', NULL, 'Pink, Silver', 'To be measured'),
(48, 7, 2, 'Olis Collections Lavender Halter Beaded Gown', 'Lavender halter-neck gown with a sweetheart neckline and a fitted bodice covered in layered diagonal beadwork. A gathered detail at the hips leads into a long skirt decorated with sparkling motifs and sheer lower panels.', 'Dress', 0.00, 'Nigerian Dresses/Olis Collections - Purple Dress.png', NULL, 'To be determined', NULL, 'Lavender, Silver', 'To be measured'),
(49, 8, 2, 'Priscer Luxe Lime Green Printed Dress', 'Fitted green dress with a sweetheart neckline, a sparkling diagonally striped bodice, and floral printed panels. Ruffled printed straps and a pale green drape across the skirt add volume and contrast.', 'Dress', 0.00, 'Nigerian Dresses/Priscer Luxe - Green Dress.png', NULL, 'To be determined', NULL, 'Lime Green, Pale Green, Yellow, Black, White', 'To be measured'),
(50, 8, 2, 'Priscer Luxe Pink and Black Printed Dress', 'Fitted pink and black dress with sheer pink lace sleeves and a black embellished bodice. A geometric printed skirt combines pink, black, cream, and gold tones, with decorative trim at the waist.', 'Dress', 0.00, 'Nigerian Dresses/Priscer Luxe - Pink and Black.png', NULL, 'To be determined', NULL, 'Pink, Black, Cream, Gold', 'To be measured'),
(51, 8, 2, 'Priscer Luxe Orange Floral Printed Dress', 'Orange floral printed dress with a sweetheart neckline and a fitted bodice outlined in sparkling trim. Long sheer sleeves and a matching sheer overlay are decorated with orange and bronze sequins.', 'Dress', 0.00, 'Nigerian Dresses/Priscer Luxe Orange Dress.png', NULL, 'To be determined', NULL, 'Orange, Lime Green, Black, Cream, Bronze', 'To be measured');

-- --------------------------------------------------------

--
-- Table structure for table `locations`
--

CREATE TABLE `locations` (
  `location_id` int(10) UNSIGNED NOT NULL,
  `location_name` varchar(100) NOT NULL,
  `address_line1` varchar(255) NOT NULL,
  `address_line2` varchar(255) DEFAULT NULL,
  `city` varchar(100) NOT NULL,
  `state` varchar(100) DEFAULT NULL,
  `postal_code` varchar(20) DEFAULT NULL,
  `country` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `occasions`
--

CREATE TABLE `occasions` (
  `occasion_id` int(10) UNSIGNED NOT NULL,
  `occasion_name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `occasions`
--

INSERT INTO `occasions` (`occasion_id`, `occasion_name`, `description`) VALUES
(1, 'Wedding', 'Wedding celebrations and related ceremonies'),
(2, 'Festival', 'Cultural festivals and celebrations'),
(3, 'Formal', 'Formal gatherings and special events');

-- --------------------------------------------------------

--
-- Table structure for table `saveditems`
--

CREATE TABLE `saveditems` (
  `saved_item_id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `item_id` int(10) UNSIGNED NOT NULL,
  `date_saved` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `sellers`
--

CREATE TABLE `sellers` (
  `seller_id` int(10) UNSIGNED NOT NULL,
  `seller_name` varchar(150) NOT NULL,
  `website_url` varchar(255) DEFAULT NULL,
  `social_url` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `location` varchar(150) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `sellers`
--

INSERT INTO `sellers` (`seller_id`, `seller_name`, `website_url`, `social_url`, `description`, `location`) VALUES
(1, 'Anita Dongre', 'https://us.anitadongre.com/', NULL, 'Indian designer fashion retailer; demonstration CultureLink listing, not a confirmed partnership.', 'India'),
(2, 'Anu Attires', 'https://www.anuattires.com/', NULL, 'Indian cultural clothing boutique featuring kurta sets, sarees, lehengas, Anarkalis, and more. Demo catalog listing; partnership not verified.', 'Dallas, Texas, USA'),
(5, 'The India Craft House', 'https://theindiacrafthouse.com/en-us', NULL, 'Indian handcrafted apparel and artisan products; demonstration listings sourced from retailer.', 'Gurgaon, Haryana, India'),
(6, 'Klothouse', NULL, NULL, NULL, NULL),
(7, 'Olis Collections', NULL, NULL, NULL, NULL),
(8, 'Priscer Luxe', NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `userlocations`
--

CREATE TABLE `userlocations` (
  `user_location_id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `location_id` int(10) UNSIGNED NOT NULL,
  `is_default` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(10) UNSIGNED NOT NULL,
  `email` varchar(150) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'customer',
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `comparisonselections`
--
ALTER TABLE `comparisonselections`
  ADD PRIMARY KEY (`comparison_id`),
  ADD UNIQUE KEY `uq_comparison_session_item` (`session_id`,`item_id`),
  ADD KEY `idx_comparison_item_id` (`item_id`),
  ADD KEY `idx_comparison_session_id` (`session_id`);

--
-- Indexes for table `cultures`
--
ALTER TABLE `cultures`
  ADD PRIMARY KEY (`culture_id`),
  ADD UNIQUE KEY `uq_culture_name` (`culture_name`);

--
-- Indexes for table `itemoccasions`
--
ALTER TABLE `itemoccasions`
  ADD PRIMARY KEY (`item_id`,`occasion_id`),
  ADD KEY `idx_itemoccasions_occasion_id` (`occasion_id`);

--
-- Indexes for table `items`
--
ALTER TABLE `items`
  ADD PRIMARY KEY (`item_id`),
  ADD KEY `idx_items_seller_id` (`seller_id`),
  ADD KEY `idx_items_culture_id` (`culture_id`),
  ADD KEY `idx_items_category` (`category`);

--
-- Indexes for table `locations`
--
ALTER TABLE `locations`
  ADD PRIMARY KEY (`location_id`);

--
-- Indexes for table `occasions`
--
ALTER TABLE `occasions`
  ADD PRIMARY KEY (`occasion_id`),
  ADD UNIQUE KEY `uq_occasion_name` (`occasion_name`);

--
-- Indexes for table `saveditems`
--
ALTER TABLE `saveditems`
  ADD PRIMARY KEY (`saved_item_id`),
  ADD UNIQUE KEY `uq_saveditems_user_item` (`user_id`,`item_id`),
  ADD KEY `idx_saveditems_user_id` (`user_id`),
  ADD KEY `idx_saveditems_item_id` (`item_id`);

--
-- Indexes for table `sellers`
--
ALTER TABLE `sellers`
  ADD PRIMARY KEY (`seller_id`);

--
-- Indexes for table `userlocations`
--
ALTER TABLE `userlocations`
  ADD PRIMARY KEY (`user_location_id`),
  ADD UNIQUE KEY `uq_user_location` (`user_id`,`location_id`),
  ADD KEY `idx_userlocations_user_id` (`user_id`),
  ADD KEY `idx_userlocations_location_id` (`location_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `uq_users_email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `comparisonselections`
--
ALTER TABLE `comparisonselections`
  MODIFY `comparison_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `cultures`
--
ALTER TABLE `cultures`
  MODIFY `culture_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `items`
--
ALTER TABLE `items`
  MODIFY `item_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=52;

--
-- AUTO_INCREMENT for table `locations`
--
ALTER TABLE `locations`
  MODIFY `location_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `occasions`
--
ALTER TABLE `occasions`
  MODIFY `occasion_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `saveditems`
--
ALTER TABLE `saveditems`
  MODIFY `saved_item_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `sellers`
--
ALTER TABLE `sellers`
  MODIFY `seller_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `userlocations`
--
ALTER TABLE `userlocations`
  MODIFY `user_location_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `comparisonselections`
--
ALTER TABLE `comparisonselections`
  ADD CONSTRAINT `fk_comparison_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `itemoccasions`
--
ALTER TABLE `itemoccasions`
  ADD CONSTRAINT `fk_itemoccasions_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_itemoccasions_occasion` FOREIGN KEY (`occasion_id`) REFERENCES `occasions` (`occasion_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `items`
--
ALTER TABLE `items`
  ADD CONSTRAINT `fk_items_culture` FOREIGN KEY (`culture_id`) REFERENCES `cultures` (`culture_id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_items_seller` FOREIGN KEY (`seller_id`) REFERENCES `sellers` (`seller_id`) ON UPDATE CASCADE;

--
-- Constraints for table `saveditems`
--
ALTER TABLE `saveditems`
  ADD CONSTRAINT `fk_saveditems_item` FOREIGN KEY (`item_id`) REFERENCES `items` (`item_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_saveditems_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `userlocations`
--
ALTER TABLE `userlocations`
  ADD CONSTRAINT `fk_userlocations_location` FOREIGN KEY (`location_id`) REFERENCES `locations` (`location_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_userlocations_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
