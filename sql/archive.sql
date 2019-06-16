CREATE TABLE IF NOT EXISTS `archive` (
	`email`  VARCHAR(255) NOT NULL,
	`createdate` TIMESTAMP,
	`serial` INT(11),
	`region_id` INT(11) default NULL,
	`template_id` INT(11) NOT NULL,
	UNIQUE  (`serial`)
) ENGINE=MyISAM DEFAULT CHARSET=UTF8;
