<!DOCTYPE HTML>
<html>
	<head>
		<title>Coinbend</title>
		<link rel="shortcut icon" type="image/png" href="favicon.ico"/>
		<meta http-equiv="content-type" content="text/html; charset=utf-8" />
		<meta name="description" content="" />
		<meta name="keywords" content="" />
		<link href="http://fonts.googleapis.com/css?family=Source+Sans+Pro:200,300,400,600,700,900" rel="stylesheet" type="text/css" />
		<script src="js/jquery.min.js"></script>
		<script src="js/jquery.dropotron.js"></script>
		<script src="js/skel.min.js"></script>
		<script src="js/skel-panels.min.js"></script>
		<script src="js/init.js"></script>
		<noscript>
			<link rel="stylesheet" href="css/skel-noscript.css" />
			<link rel="stylesheet" href="css/style.css" />
			<link rel="stylesheet" href="css/style-desktop.css" />
		</noscript>
		<!--[if lte IE 8]><script src="js/html5shiv.js"></script><link rel="stylesheet" href="css/ie8.css" /><![endif]-->
		<script>
	$(function(){
	  $(window).scroll(function(){
		var scroll_position = $(this).scrollTop();
		var n = 590;
		var window_height = $(window).height();
		var document_height = $(document).height();
		if(scroll_position < 3 && window_height < 1100){
			$(".main-text").fadeTo(5, 0.10);
		}
		if(scroll_position > 10 && scroll_position <= n){
			$(".main-text").fadeTo(5, 1.0);
		}
		if(scroll_position > n){
			$(".fade-box").fadeTo(5, 0.20);
		}
		else{
			$(".fade-box").fadeTo(5, 1.0);
		}

		//Fix Firefox bug when using zoom CSS
		if(scroll_position > 772){
			$('html, body').scrollTop(772);
		}
	  });
	});
		</script>
	</head>
	<body class="homepage">
		<!-- Header Wrapper -->
			<audio src="select_sound.mp3" preload="auto" id="select-sound"></audio>
			<div id="header-wrapper" class="skel-panels-fixed">
						
				<!-- Header -->
					<div id="header" class="container">
						
						<!-- Logo -->
							<h1><a href="http://www.twitter.com/Coinbend" id="logo">@Coinbend</a></h1>
						
						<!-- Nav -->
							<nav id="nav">
								<ul>

<li><a href="#bottom">Download</a></li>        
                          			
	

<li style="-moz-user-select: none; cursor: pointer; white-space: nowrap; opacity: 1;" class="opener">
   <span>Contact</span>
   <ul style="-moz-user-select: none; position: absolute; z-index: 1000; left: 39.2px; top: 71px; opacity: 1; display: none;" class="dropotron dropotron-level-0 center">
	<li style="white-space: nowrap;"><a href="mailto:coinbend@gmail.com" style="display: block;">coinbend@gmail.com</a></li>
      <li style="white-space: nowrap;"><a href="https://bitcointalk.org/index.php?action=profile;u=531479" style="display: block;">Bitcointalk</a></li>
      <li style="white-space: nowrap;"><a href="http://www.facebook.com/Coinbend" style="display: block;">Facebook</a></li>
      <li style="white-space: nowrap;"><a href="http://www.youtube.com/Coinbend" style="display: block;">YouTube</a></li>
      <li style="white-space: nowrap;"><a href="http://www.twitter.com/Coinbend" style="display: block;">Twitter</a></li>
   </ul>
</li>

<li style="-moz-user-select: none; cursor: pointer; white-space: nowrap; opacity: 1;" class="opener">
   <span>Demo</span>
   <ul style="-moz-user-select: none; position: absolute; z-index: 1000; left: 39.2px; top: 71px; opacity: 1; display: none;" class="dropotron dropotron-level-0 center">
	<li style="white-space: nowrap;"><a href="http://alice.coinbend.com/" style="display: block;">Alice</a></li>
      <li style="white-space: nowrap;"><a href="http://bob.coinbend.com/" style="display: block;">Bob</a></li>
   </ul>
</li>


                                          <li><a href="http://www.coinbend.com/whitepaper.pdf">Whitepaper</a></li>        
                          			
									<li><a href="http://www.github.com/robertsdotpm/coinbend">Source Code</a></li>


								</ul>
							</nav>

					</div>

			</div>
		<!-- /Header Wrapper -->

		<!-- Main Wrapper -->
			<div id="main-wrapper">

				<!-- Main -->
					<section id="banner" class="container">
					
						<div class="row">
							<div id="content" class="12u">
                                <div class="fade-box">
									<header class="major">
										<h2>In eight words:</h2>
										<span class="byline">
Coinbend lets you swap alt-coins with complete strangers.
</span>
									</header>
									
									<div class="row">
										<section class="4u">
											<span class="pennant tiles"><span class="icon icon-lock"></span></span>
											<div class="main-text">
											<header>
												<h2>Provably safe</h2>
											</header>
											<p>Master your money by trading directly with people via the blockchain.<br>Deposits are not required.</p>
											</div>
										</section>
										<section class="4u">
											<span class="pennant tiles"><span class="icon icon-exchange"></span></span>
											<div class="main-text">
											<header>
												<h2>Multi-currency</h2>
											</header>
											<p>Hundreds of alt-coins are supported! Trade bitcoin, litecoin, dogecoin<br>and emerging altcoins.
											</div>
										</section>
										<section class="4u">
											<span class="pennant tiles"><span class="icon icon-group"></span></span>
											<div class="main-text">
											<header>
												<h2>Open trading</h2>
											</header>
											<p>Coinbend requires no registration.<br> 
											    It's open, decentralized, P2P<br>and run by the users.</p>
											</div>
										<a name="bottom"></a>
										</section>
									</div>
								</div>
								<div class="actions">
									<span class="byline">This project is currently in pre-alpha stage.</span>
									<a href="<?php
	$agent = $_SERVER['HTTP_USER_AGENT'];
	if(preg_match('/Linux/',$agent))
	{
		echo("linux.zip");
	}
	else
	{
		echo("windows.zip");
	}
?>" class="button button-big">Download Now</a>
								</div>

							</div>
						</div>

					</section>
				<!-- Main -->

			</div>
		<!-- /Main Wrapper -->


	<script>
	/*
You will never get to hear these tacky sounds.
var tiles = $(".tiles");
tiles.hover(function(){
   $("#select-sound")[0].play();
}, function(){
   $("#select-sound")[0].pause();
});
*/
	</script>
	</body>
</html>
