<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:fn="http://www.w3.org/2005/xpath-functions" xmlns:df="http://usawa.defalsify.org/">
	<xsl:template match="/">
		<html>
			<head>
				<title>Accounting</title>
			</head>
			<body>
				<xsl:apply-templates select="df:ledger" />
			</body>
		</html>
	</xsl:template>

	<xsl:template match="/df:ledger">
		<p>Documento recuperado: <xsl:value-of select="df:retrieved" /> from <xsl:value-of select="df:src" /></p>
		<xsl:for-each select="df:entry">
			<p><xsl:value-of select="df:data/df:serial" />:<xsl:value-of select="df:data/df:date" />:<xsl:value-of select="df:data/df:ref" /></p>
		</xsl:for-each>
	</xsl:template>

</xsl:stylesheet>
