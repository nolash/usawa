<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fn="http://www.w3.org/2005/xpath-functions">
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
		<p>Documento recuperado: <xsl:value-of select="retrieved" /> from <xsl:value-of select="src" /></p>
		<xsl:for-each select="entry">
			<p><xsl:value-of select="data/serial" />:<xsl:value-of select="data/date" />:<xsl:value-of select="data/ref" /></p>
		</xsl:for-each>
	</xsl:template>

</xsl:stylesheet>
