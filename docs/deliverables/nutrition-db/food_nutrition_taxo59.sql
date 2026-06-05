-- 음식 클래스별 영양소 (taxo59, 100g 기준 클래스 평균) — DB 적재용
-- 생성: 2026-06-04 | 출처: AIHub 음식이미지 라벨 nutrition 필드 (100g 정규화 후 클래스 내 음식 평균)
-- ⚠ 데모용 추정치(클래스 평균). 모델 detection 출력의 class명(class_en)과 1:1 매칭(조인 키).

DROP TABLE IF EXISTS food_nutrition;
CREATE TABLE food_nutrition (
    class_en        VARCHAR(40) PRIMARY KEY,        -- 모델 클래스명(영문, taxo59) = 조인 키
    class_ko        VARCHAR(40) NOT NULL,           -- 한글 표시명
    n_source_codes  SMALLINT,                       -- 평균에 사용된 AIHub 원본코드 수
    serving_g       NUMERIC(6,1),                   -- 1인분 평균 중량(g)
    kcal_100g       NUMERIC(7,2),                   -- 열량 (kcal / 100g)
    carb_g          NUMERIC(6,2),                   -- 탄수화물 (g / 100g)
    sugar_g         NUMERIC(6,2),                   -- 당류 (g / 100g)
    fat_g           NUMERIC(6,2),                   -- 지방 (g / 100g)
    protein_g       NUMERIC(6,2),                   -- 단백질 (g / 100g)
    sodium_mg       NUMERIC(8,2),                   -- 나트륨 (mg / 100g)
    chol_mg         NUMERIC(7,2),                   -- 콜레스테롤 (mg / 100g)
    sat_fat_g       NUMERIC(6,2),                   -- 포화지방 (g / 100g)
    trans_fat_g     NUMERIC(6,2)                    -- 트랜스지방 (g / 100g)
);
COMMENT ON TABLE food_nutrition IS 'taxo59 음식 클래스별 영양소(100g 기준 평균). 모델 detection 출력과 class_en으로 조인.';

INSERT INTO food_nutrition VALUES ('barbecue-ribs', '갈비', 7, 266, 188.96, 10.29, 3.54, 11.99, 10.81, 560.34, 43.6, 2.52, 0.03);
INSERT INTO food_nutrition VALUES ('black-bean-noodles', '짜장면', 3, 483, 111.72, 17.02, 5.92, 1.95, 6.14, 236.19, 8.68, 0.33, 0.03);
INSERT INTO food_nutrition VALUES ('braised-chicken', '찜닭', 3, 314, 126.63, 7.16, 0.78, 6.56, 9.68, 193.47, 3.77, 0.02, 0.0);
INSERT INTO food_nutrition VALUES ('braised-pork-hock', '족발', 3, 310, 194.99, 11.34, 6.85, 8.55, 16.5, 497.51, 57.55, 2.35, 0.0);
INSERT INTO food_nutrition VALUES ('bread', '빵', 45, 150, 274.41, 37.4, 9.14, 10.77, 7.34, 238.68, 57.54, 3.48, 0.37);
INSERT INTO food_nutrition VALUES ('bulgogi', '불고기', 3, 237, 144.91, 6.97, 2.27, 8.43, 10.12, 224.22, 27.08, 2.79, 0.0);
INSERT INTO food_nutrition VALUES ('cake', '케이크', 8, 182, 321.6, 35.09, 13.84, 18.06, 4.64, 146.36, 69.69, 3.71, 0.12);
INSERT INTO food_nutrition VALUES ('cold-noodles', '냉면', 4, 328, 166.23, 28.53, 1.85, 2.13, 7.8, 472.95, 31.89, 0.53, 0.02);
INSERT INTO food_nutrition VALUES ('cold-ramen', '냉라멘', 1, 312, 160.94, 23.54, 4.18, 4.11, 6.38, 515.51, 45.47, 0.78, 0.16);
INSERT INTO food_nutrition VALUES ('curry', '카레', 8, 308, 153.67, 12.16, 1.74, 9.24, 5.9, 529.23, 30.36, 3.07, 0.41);
INSERT INTO food_nutrition VALUES ('dim-sum', '딤섬(찐만두)', 2, 272, 364.27, 34.71, 4.29, 19.3, 10.55, 149.78, 17.38, 7.5, 0.07);
INSERT INTO food_nutrition VALUES ('doenjang-jjigae', '된장찌개', 2, 300, 103.87, 4.48, 0.57, 6.75, 6.35, 378.21, 20.1, 2.01, 0.11);
INSERT INTO food_nutrition VALUES ('dumplings', '만두', 9, 189, 203.66, 30.86, 3.05, 4.55, 8.28, 404.91, 13.22, 0.48, 0.19);
INSERT INTO food_nutrition VALUES ('fish-cake', '어묵', 2, 110, 191.01, 16.52, 1.51, 7.81, 12.91, 401.07, 53.03, 0.57, 1.69);
INSERT INTO food_nutrition VALUES ('fried-chicken', '후라이드치킨', 43, 217, 236.26, 21.37, 4.98, 11.69, 11.37, 355.92, 14.93, 0.4, 0.83);
INSERT INTO food_nutrition VALUES ('fried-food-platter', '튀김(모둠)', 3, 124, 231.65, 18.34, 0.6, 11.86, 12.18, 486.79, 45.49, 0.37, 1.15);
INSERT INTO food_nutrition VALUES ('fried-rice', '볶음밥', 2, 247, 176.6, 31.5, 0.58, 1.89, 6.98, 223.89, 109.53, 0.64, NULL);
INSERT INTO food_nutrition VALUES ('grilled-beef', '소고기구이', 2, 260, 176.61, 15.05, 5.96, 9.0, 8.29, 388.61, 43.95, 3.51, 0.0);
INSERT INTO food_nutrition VALUES ('grilled-fish', '생선구이', 7, 74, 191.08, 0.46, NULL, 10.66, 21.69, 400.21, 61.25, 9.47, 0.68);
INSERT INTO food_nutrition VALUES ('grilled-pork-belly', '삼겹살', 1, 205, 220.4, 3.14, NULL, 18.2, 10.81, 159.28, 32.15, 9.28, 0.0);
INSERT INTO food_nutrition VALUES ('hamburger', '햄버거', 5, 227, 179.43, 16.68, 0.87, 7.15, 12.01, 293.58, 21.27, 1.34, 0.35);
INSERT INTO food_nutrition VALUES ('hot-pot', '전골', 6, 430, 65.83, 8.3, 0.58, 1.67, 5.05, 345.89, 13.61, 0.19, 0.0);
INSERT INTO food_nutrition VALUES ('japanese-ramen', '일본라멘', 5, 496, 114.82, 13.52, 0.77, 4.51, 4.51, 400.73, 110.56, 1.61, 0.02);
INSERT INTO food_nutrition VALUES ('jjamppong', '짬뽕', 5, 537, 142.15, 24.79, 0.77, 1.88, 5.94, 813.65, 2.85, 0.19, 0.12);
INSERT INTO food_nutrition VALUES ('jjigae-red', '빨간찌개', 4, 371, 75.39, 4.1, 1.32, 3.92, 6.14, 452.91, 26.57, 0.44, 0.0);
INSERT INTO food_nutrition VALUES ('kalguksu', '칼국수', 5, 512, 95.03, 17.27, 1.64, 0.55, 4.29, 319.28, 2.54, 0.07, 0.0);
INSERT INTO food_nutrition VALUES ('korean-blood-sausage', '순대', 3, 206, 151.63, 13.05, 0.01, 6.47, 9.68, 476.18, 95.94, 2.04, 0.0);
INSERT INTO food_nutrition VALUES ('korean-clear-soup', '맑은국', 12, 539, 68.76, 4.42, 1.25, 2.87, 6.29, 228.49, 18.03, 0.13, 0.01);
INSERT INTO food_nutrition VALUES ('korean-ramyeon-red', '라면', 3, 519, 144.39, 19.87, NULL, 4.69, 5.41, 382.55, 55.07, 1.09, 0.03);
INSERT INTO food_nutrition VALUES ('korean-red-soup', '빨간국', 6, 600, 23.74, 2.07, 0.14, 0.73, 2.58, 158.81, 23.29, 0.07, 0.01);
INSERT INTO food_nutrition VALUES ('mixed-rice-bowl', '비빔밥', 5, 362, 171.98, 28.75, 1.32, 3.65, 5.82, 236.23, 28.16, 0.47, 0.11);
INSERT INTO food_nutrition VALUES ('nagasaki-champon', '나가사끼짬뽕', 1, 398, 121.89, 18.68, NULL, 1.9, 6.6, 730.96, 90.27, 0.2, NULL);
INSERT INTO food_nutrition VALUES ('noodle-plain', '국수', 4, 500, 87.15, 13.18, 0.52, 1.5, 4.65, 240.72, 7.29, 0.14, 0.0);
INSERT INTO food_nutrition VALUES ('pasta', '파스타', 18, 359, 245.87, 27.11, 0.98, 12.03, 7.24, 366.43, 28.99, 1.5, 0.02);
INSERT INTO food_nutrition VALUES ('pizza', '피자', 29, 193, 199.4, 26.51, 2.46, 6.27, 7.71, 2609.22, 13.61, 1.58, 0.08);
INSERT INTO food_nutrition VALUES ('pork-cutlet-dry', '돈가스', 6, 194, 241.61, 24.75, 7.7, 9.64, 12.69, 204.08, 65.13, 1.93, 0.87);
INSERT INTO food_nutrition VALUES ('pork-cutlet-sauced', '소스돈가스', 3, 273, 187.28, 18.03, 1.02, 8.83, 8.44, 431.33, 79.39, 0.63, 0.76);
INSERT INTO food_nutrition VALUES ('raw-fish', '회', 7, 236, 114.61, 10.22, 2.17, 2.52, 12.11, 258.22, 13.37, 0.3, 0.01);
INSERT INTO food_nutrition VALUES ('rice-bowl', '덮밥', 15, 327, 222.6, 33.27, 2.02, 5.7, 8.6, 264.44, 62.97, 0.99, 0.25);
INSERT INTO food_nutrition VALUES ('rice-noodle-soup', '쌀국수', 11, 594, 97.96, 15.58, 0.19, 2.25, 3.53, 278.83, 71.22, 0.44, 0.02);
INSERT INTO food_nutrition VALUES ('rice-porridge', '죽', 8, 205, 227.06, 28.74, 15.85, 10.53, 4.79, 278.4, 32.43, 3.77, 0.25);
INSERT INTO food_nutrition VALUES ('rice-soup', '국밥', 3, 517, 91.34, 17.51, NULL, 0.71, 3.55, 192.17, 3.45, 0.06, 0.01);
INSERT INTO food_nutrition VALUES ('salad', '샐러드', 11, 134, 129.18, 10.64, 1.78, 7.52, 5.57, 128.31, 21.84, 1.17, 0.03);
INSERT INTO food_nutrition VALUES ('sandwich', '샌드위치', 26, 195, 242.8, 22.36, 1.77, 13.77, 8.34, 445.3, 53.57, 4.47, 0.21);
INSERT INTO food_nutrition VALUES ('savory-pancake', '전/부침개', 3, 217, 171.05, 23.73, NULL, 4.55, 8.15, 318.42, 10.99, 0.27, 0.78);
INSERT INTO food_nutrition VALUES ('seafood-clear-tang', '해물맑은탕', 4, 488, 119.78, 8.15, 0.13, 3.34, 13.86, 394.08, 14.21, 0.09, 0.06);
INSERT INTO food_nutrition VALUES ('seafood-jjim', '해물찜', 2, 203, 183.68, 15.75, 7.8, 2.61, 26.34, 491.8, 0.0, 0.08, 0.0);
INSERT INTO food_nutrition VALUES ('seafood-spicy-tang', '해물매운탕', 4, 384, 50.81, 3.86, 1.0, 0.98, 7.18, 377.56, 16.32, 0.09, 0.0);
INSERT INTO food_nutrition VALUES ('seaweed-rice-roll', '김밥', 10, 205, 232.96, 37.97, 1.75, 5.11, 7.51, 372.18, 46.19, 0.51, 0.3);
INSERT INTO food_nutrition VALUES ('shrimp-dish', '새우요리', 6, 204, 187.18, 14.24, 6.41, 8.44, 12.6, 491.62, 79.18, 0.93, 0.69);
INSERT INTO food_nutrition VALUES ('spicy-mixed-noodles', '비빔국수', 2, 175, 230.02, 47.3, 3.88, 0.77, 6.54, 448.53, 0.54, 0.08, 0.0);
INSERT INTO food_nutrition VALUES ('squid-dish', '오징어요리', 1, 142, 74.2, 2.4, NULL, 1.74, 11.88, 573.77, 10.29, 0.33, 0.01);
INSERT INTO food_nutrition VALUES ('sushi', '초밥', 9, 221, 248.86, 36.9, 3.29, 3.55, 15.17, 536.98, 111.78, 0.69, 0.02);
INSERT INTO food_nutrition VALUES ('takoyaki', '타코야키', 1, 206, 161.46, 15.56, 1.65, 8.26, 5.23, 120.11, 36.6, 0.49, 0.77);
INSERT INTO food_nutrition VALUES ('tteokbokki-cream-rose', '로제떡볶이', 4, 271, 208.43, 29.63, 1.28, 7.79, 4.62, 317.06, 43.62, 0.91, 0.03);
INSERT INTO food_nutrition VALUES ('tteokbokki-jajang', '짜장떡볶이', 1, 240, 190.0, 34.59, 0.5, 3.08, 5.53, 422.38, 7.72, 0.66, 0.02);
INSERT INTO food_nutrition VALUES ('tteokbokki-red', '떡볶이', 6, 280, 199.53, 33.73, 3.77, 4.42, 6.17, 458.77, 7.84, 1.06, 0.05);
INSERT INTO food_nutrition VALUES ('udon', '우동', 4, 468, 92.39, 10.01, NULL, 4.27, 2.51, 233.21, 9.31, 0.34, 0.01);
INSERT INTO food_nutrition VALUES ('western-cream-soup', '양식수프', 5, 274, 139.17, 16.24, 0.36, 5.84, 5.05, 527.14, 14.95, 1.38, 0.07);
