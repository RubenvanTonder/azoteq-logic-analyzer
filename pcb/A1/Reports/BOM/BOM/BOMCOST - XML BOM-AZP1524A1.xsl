<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Bill of Materials</title>
      </head>
      <body>
        <table style="font:8pt Segoe UI" border="1" cellspacing="0" cellpadding="1" bgcolor="#FFFFFF">
          <thead style="font:bold; background-color:#C0C0C0">
            <tr valign="top">
              <xsl:for-each select="/GRID/COLUMNS/COLUMN">
                <td align="center">
                  <xsl:attribute name="width">
                    <xsl:value-of select="@Width" />
                  </xsl:attribute>
                  <xsl:value-of select="@Caption" />
                </td>
              </xsl:for-each>
            </tr>
          </thead>
          <xsl:for-each select="/GRID/ROWS/ROW">
            <tr valign="top">
              <td align="left">
                <xsl:value-of select="@Designator" />
                <xsl:if test="@Designator[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Pin_Count" />
                <xsl:if test="@Pin_Count[.='']">&#160;</xsl:if>
              </td>
              <td align="right">
                <xsl:value-of select="@Quantity" />
                <xsl:if test="@Quantity[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___BONDING_POINTS" />
                <xsl:if test="@ASSY___BONDING_POINTS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___CONFORMAL_COATING" />
                <xsl:if test="@ASSY___CONFORMAL_COATING[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___INSPECTION_STEPS" />
                <xsl:if test="@ASSY___INSPECTION_STEPS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___PCB_SEPERATION" />
                <xsl:if test="@ASSY___PCB_SEPERATION[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___PLASTIC_ASSY" />
                <xsl:if test="@ASSY___PLASTIC_ASSY[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___TERMINALS" />
                <xsl:if test="@ASSY___TERMINALS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___TEST_STEPS" />
                <xsl:if test="@ASSY___TEST_STEPS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___TRANSPORT" />
                <xsl:if test="@ASSY___TRANSPORT[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___WASHING" />
                <xsl:if test="@ASSY___WASHING[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___WIRES" />
                <xsl:if test="@ASSY___WIRES[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_COLOUR" />
                <xsl:if test="@PCB_COLOUR[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_WIDTH" />
                <xsl:if test="@PCB_WIDTH[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_PLATING_FINISH" />
                <xsl:if test="@PCB_PLATING_FINISH[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_THICKNESS" />
                <xsl:if test="@PCB_THICKNESS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_TYPE" />
                <xsl:if test="@PCB_TYPE[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Footprint" />
                <xsl:if test="@Footprint[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___PACKAGING" />
                <xsl:if test="@ASSY___PACKAGING[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Name" />
                <xsl:if test="@Name[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Int_Part_Number" />
                <xsl:if test="@Int_Part_Number[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Library_Name" />
                <xsl:if test="@Library_Name[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Library_Reference" />
                <xsl:if test="@Library_Reference[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@LibRef" />
                <xsl:if test="@LibRef[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_LAYER_QTY" />
                <xsl:if test="@PCB_LAYER_QTY[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@REVISION_PCB" />
                <xsl:if test="@REVISION_PCB[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@REVISION_SCH" />
                <xsl:if test="@REVISION_SCH[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Type" />
                <xsl:if test="@Type[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Value" />
                <xsl:if test="@Value[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___DOUBLE_SIDED_ASSY" />
                <xsl:if test="@ASSY___DOUBLE_SIDED_ASSY[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_PLATING_THICKNESS" />
                <xsl:if test="@PCB_PLATING_THICKNESS[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@PCB_LENGTH" />
                <xsl:if test="@PCB_LENGTH[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@Alternative_SAP_Nr" />
                <xsl:if test="@Alternative_SAP_Nr[.='']">&#160;</xsl:if>
              </td>
              <td align="left">
                <xsl:value-of select="@ASSY___PCB_SPECIAL_OPERATIONS" />
                <xsl:if test="@ASSY___PCB_SPECIAL_OPERATIONS[.='']">&#160;</xsl:if>
              </td>
            </tr>
          </xsl:for-each>
        </table>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>