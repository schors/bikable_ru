CREATE TABLE IF NOT EXISTS `templates` (
	`id` int(11) NOT NULL auto_increment,
	`name`  VARCHAR(255) NOT NULL,
	`sort`  INT(11) default 0,
	`updatetime` TIMESTAMP,
	`who`  VARCHAR(255) default NULL,
	`uniq` CHAR(32) NOT NULL,
	`funiq` CHAR(8) NOT NULL,
	`pub` TINYINT(1) default 0,
	`cnt` INT(11) default 0,
	`region_id` INT(11) default NULL,
	PRIMARY KEY  (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=UTF8;
