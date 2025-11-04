<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:template match="/">
		<html>
			<head>
				<title>Accounting</title>
			</head>
			<body>
				<xsl:apply-templates select="ledger" />
			</body>
		</html>
	</xsl:template>

	<xsl:template match="/ledger">
		<p>Document retrieved: <xsl:value-of select="retrieved" /></p>
		<xsl:apply-templates select="entry" />
	</xsl:template>

	<xsl:template match="entry">
		<p>ref: <xsl:value-of select="data/ref" /></p>
	</xsl:template>
</xsl:stylesheet>
