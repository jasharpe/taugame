<?php

mkdir("cards_cmyk");

function rewrite($old, $new) {
  $back_img = new Imagick($old);
  $new_back_img = new Imagick();
  $new_back_img->newImage(825, 1125, '#FFFFFF');
  $new_back_img->compositeImage($back_img, Imagick::COMPOSITE_DEFAULT, 0, 0);
  $new_back_img->transformImageColorspace(Imagick::COLORSPACE_CMYK);
  $new_back_img->writeImage($new);
}

rewrite("bqtau_back.png", "bqtau_back_rewritten.png");
rewrite("bqtau_cover.png", "bqtau_cover_rewritten.png");
rewrite("rules1.png", "rules1_rewritten.png");
rewrite("rules2.png", "rules2_rewritten.png");
rewrite("rules3.png", "rules3_rewritten.png");

foreach(glob("cards/*.png") as $filename) {
	$img = new Imagick($filename);
	$img->transformImageColorspace(Imagick::COLORSPACE_CMYK);
	preg_match('/\/[\w]*.png/',$filename,$newname);
	$img->writeImage("cards_cmyk".$newname[0]);
}

$card_images = array();
foreach(glob("cards_cmyk/*.png") as $filename) {
	$card_images[] = $filename;
}
// TODO: reorder the card images.

// Add the back image interleaved with the front images.
$images = array();
$images[] = "bqtau_cover_rewritten.png";
$images[] = "rules1_rewritten.png";
$images[] = "rules2_rewritten.png";
$images[] = "rules3_rewritten.png";
foreach(array_reverse($card_images) as $card_image) {
	$images[] = "bqtau_back_rewritten.png";
	$images[] = $card_image;
}

$img = new Imagick();
$img->setResolution(300, 300);
$img->readImages($images);
$img->setImageUnits(Imagick::RESOLUTION_PIXELSPERINCH);
$img->setImageFormat("pdf");
$img->writeImages('card_test.pdf', true);

