CREATE TABLE IF NOT EXISTS `users` (
	`id` int(11) NOT NULL auto_increment,
	`email` VARCHAR(255) NOT NULL,
	`name`  VARCHAR(255) NOT NULL,
	`password` VARCHAR(255),
	`code`  CHAR(32),
	`priv`  TINYINT(1) default 0,
	`valid` TINYINT(1) default 0,
	`lock`  TINYINT(1) default 0,
	`region_id` INT(11) default NULL,
	PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=UTF8;
