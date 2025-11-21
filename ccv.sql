CREATE DATABASE  IF NOT EXISTS `ccv`;
USE `ccv`;

--
-- Table structure for table `audit_log`
--

DROP TABLE IF EXISTS `audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `carrier_id` int DEFAULT NULL,
  `action_type` varchar(50) DEFAULT NULL,
  `description` text,
  `changed_by` varchar(100) DEFAULT NULL,
  `changed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_log`
--

INSERT INTO `audit_log` VALUES (1,12,'update','Updated payer_id','Crowdsource: Tosin','2025-11-21 10:42:59');

--
-- Table structure for table `carrier_edits`
--

DROP TABLE IF EXISTS `carrier_edits`;
CREATE TABLE `carrier_edits` (
  `edit_id` int NOT NULL AUTO_INCREMENT,
  `carrier_id` int DEFAULT NULL,
  `naic_code` varchar(10) DEFAULT NULL,
  `submitter_name` varchar(255) DEFAULT NULL,
  `submitter_email` varchar(255) DEFAULT NULL,
  `field_name` varchar(50) DEFAULT NULL,
  `old_value` text,
  `new_value` text,
  `status` varchar(20) DEFAULT 'pending',
  `submitted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `reviewed_by` int DEFAULT NULL,
  `reviewed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`edit_id`),
  KEY `carrier_id` (`carrier_id`),
  CONSTRAINT `carrier_edits_ibfk_1` FOREIGN KEY (`carrier_id`) REFERENCES `carriers` (`carrier_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `carrier_edits`
--

INSERT INTO `carrier_edits` VALUES (1,12,NULL,'Tosin','tosinajy@gmail.com','payer_id','','10000','approved','2025-11-21 10:42:11',1,'2025-11-21 10:42:59');

--
-- Table structure for table `carriers`
--

DROP TABLE IF EXISTS `carriers`;
CREATE TABLE `carriers` (
  `carrier_id` int NOT NULL AUTO_INCREMENT,
  `legal_name` varchar(255) NOT NULL,
  `naic_code` varchar(10) NOT NULL,
  `payer_id` varchar(10) DEFAULT NULL,
  `contact_phone` varchar(20) DEFAULT NULL,
  `website_url` varchar(255) DEFAULT NULL,
  `state_domicile` varchar(2) DEFAULT NULL,
  `last_updated` date DEFAULT NULL,
  `address_claims_street` varchar(255) DEFAULT NULL,
  `address_claims_city` varchar(100) DEFAULT NULL,
  `address_claims_state` varchar(2) DEFAULT NULL,
  `address_claims_zip` varchar(10) DEFAULT NULL,
  `phone_claims` varchar(20) DEFAULT NULL,
  `phone_prior_auth` varchar(20) DEFAULT NULL,
  `phone_eligibility` varchar(20) DEFAULT NULL,
  `line_of_business` varchar(50) DEFAULT NULL COMMENT 'e.g., Commercial, Medicare, Medicaid',
  `am_best_rating` varchar(50) DEFAULT NULL,
  `enrollment` bit(1) DEFAULT b'0',
  `attachment` bit(1) DEFAULT b'0',
  `transaction` varchar(1000) DEFAULT NULL,
  `wc_auto` bit(1) DEFAULT b'0',
  PRIMARY KEY (`carrier_id`),
  KEY `idx_legal_name` (`legal_name`),
  KEY `idx_naic_code` (`naic_code`),
  KEY `idx_payer_id` (`payer_id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `carriers`
--

INSERT INTO `carriers` VALUES (10,'Blue Cross Blue Shield of Texas','12345','BCBS01','800-555-0199','https://www.bcbstx.com','TX','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(11,'UnitedHealthcare','67890','87726','800-555-0299','https://www.uhc.com','MN','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(12,'Humana Insurance Company','11223','10000','800-555-0399','https://www.aetna.com','CT','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(13,'United HealthCare Insurance Company','12345','UHC01','800-555-1212','https://www.uhc.com','MN','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(14,'Aetna Life Insurance Company','67890','AETNA','888-222-3333','https://www.aetna.com','CT','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(15,'Progressive Casualty Insurance Company','54321',NULL,'800-776-4737','https://www.progressive.com','OH','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(16,'United Healthcare Group Insurance Company','79456','87765','1-800-456-7890','https://www.uhc.com/providers','MN','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(17,'GEICO Indemnity Company','35882','GEC01','1-800-841-3000','https://www.geico.com/claims','MD','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0'),(18,'State Farm Mutual Automobile Insurance Company','25178','SFI01','1-800-440-0900','https://www.statefarm.com/agent','IL','2025-11-21',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,_binary '\0',_binary '\0',NULL,_binary '\0');

--
-- Table structure for table `naic_data`
--

DROP TABLE IF EXISTS `naic_data`;
CREATE TABLE `naic_data` (
  `naic_id` int NOT NULL AUTO_INCREMENT,
  `carrier_id` int DEFAULT NULL,
  `cocode` varchar(20) DEFAULT NULL,
  `company_name` varchar(1000) DEFAULT NULL,
  `full_company_name` varchar(1000) DEFAULT NULL,
  `short_name` varchar(255) DEFAULT NULL,
  `website` varchar(255) DEFAULT NULL,
  `insurance_types` varchar(255) DEFAULT NULL,
  `company_licensed_in` varchar(255) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `address_line_1` varchar(255) DEFAULT NULL,
  `address_line_2` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `state` varchar(2) DEFAULT NULL,
  `zip` varchar(20) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `business_type_code` varchar(2) DEFAULT NULL,
  PRIMARY KEY (`naic_id`),
  UNIQUE KEY `carrier_id` (`carrier_id`),
  UNIQUE KEY `cocode` (`cocode`),
  CONSTRAINT `naic_data_ibfk_1` FOREIGN KEY (`carrier_id`) REFERENCES `carriers` (`carrier_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `naic_data`
--


--
-- Table structure for table `other_payer_names`
--

DROP TABLE IF EXISTS `other_payer_names`;
CREATE TABLE `other_payer_names` (
  `id` int NOT NULL AUTO_INCREMENT,
  `carrier_id` int DEFAULT NULL,
  `payer_id` varchar(50) DEFAULT NULL,
  `payer_name` varchar(255) DEFAULT NULL,
  `source` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `carrier_id` (`carrier_id`),
  CONSTRAINT `other_payer_names_ibfk_1` FOREIGN KEY (`carrier_id`) REFERENCES `carriers` (`carrier_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `other_payer_names`
--


--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) DEFAULT 'admin',
  `email` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

INSERT INTO `users` VALUES (1,'admin','scrypt:32768:8:1$MzgXhF0gLHwNmLk9$bd48d7ca43190112fe4cdfa519001ba0225cc16edcb13aeabc2808b63177186ed323d149456a23a08958989eedc26339df0ade6565f5228906eac92e270889cd','admin','admin@example.com','2025-11-21 05:42:35');

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed
