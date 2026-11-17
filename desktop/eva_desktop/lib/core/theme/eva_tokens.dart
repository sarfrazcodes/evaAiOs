import 'package:flutter/material.dart';

enum EvaDensity {
  compact('Compact', 0.85, 6.0, 10.0),
  comfortable('Comfortable', 1.0, 10.0, 16.0),
  spacious('Spacious', 1.15, 14.0, 20.0);

  final String label;
  final double scale;
  final double verticalPadding;
  final double horizontalPadding;
  const EvaDensity(this.label, this.scale, this.verticalPadding, this.horizontalPadding);
}

class EvaTokens {
  // Spacing
  static const double space2 = 2.0;
  static const double space4 = 4.0;
  static const double space6 = 6.0;
  static const double space8 = 8.0;
  static const double space12 = 12.0;
  static const double space16 = 16.0;
  static const double space20 = 20.0;
  static const double space24 = 24.0;
  static const double space32 = 32.0;
  static const double space40 = 40.0;

  // Radii
  static const double radiusSm = 4.0;
  static const double radiusMd = 8.0;
  static const double radiusLg = 12.0;
  static const double radiusPill = 999.0;

  static final BorderRadius borderSm = BorderRadius.circular(radiusSm);
  static final BorderRadius borderMd = BorderRadius.circular(radiusMd);
  static final BorderRadius borderLg = BorderRadius.circular(radiusLg);
  static final BorderRadius borderPill = BorderRadius.circular(radiusPill);

  // Dimensions
  static const double topBarHeight = 44.0;
  static const double sidebarExpandedWidth = 210.0;
  static const double sidebarCollapsedWidth = 64.0;
  static const double maxContentWidth = 1100.0;

  // Typography helpers
  static TextStyle fontTitle(Color color, {double scale = 1.0}) => TextStyle(
        fontFamily: 'Inter',
        color: color,
        fontSize: 18 * scale,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.2,
      );

  static TextStyle fontSection(Color color, {double scale = 1.0}) => TextStyle(
        fontFamily: 'Inter',
        color: color,
        fontSize: 14 * scale,
        fontWeight: FontWeight.w600,
      );

  static TextStyle fontBody(Color color, {double scale = 1.0, FontWeight weight = FontWeight.normal}) => TextStyle(
        fontFamily: 'Inter',
        color: color,
        fontSize: 13 * scale,
        fontWeight: weight,
        height: 1.45,
      );

  static TextStyle fontCaption(Color color, {double scale = 1.0}) => TextStyle(
        fontFamily: 'Inter',
        color: color,
        fontSize: 11 * scale,
        fontWeight: FontWeight.w500,
      );

  static TextStyle fontCode(Color color, {double scale = 1.0}) => TextStyle(
        fontFamily: 'monospace',
        color: color,
        fontSize: 12 * scale,
      );
}
