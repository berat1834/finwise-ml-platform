"""
AWS Bağlantı Testi
==================
boto3 ile AWS kimlik bilgilerini doğrular ve temel bağlantıyı test eder.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import sys

def test_aws_connection():
    """AWS kimlik bilgilerini ve bağlantısını test et."""
    
    print("=" * 60)
    print("AWS BAĞLANTI TESTİ")
    print("=" * 60)
    
    try:
        # 1. Kimlik bilgilerini kontrol et
        print("\n[1/3] Kimlik bilgileri kontrol ediliyor...")
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("✗ HATA: AWS kimlik bilgileri bulunamadı!")
            print("\nLütfen şu dosyayı oluşturun: C:\\Users\\berat\\.aws\\credentials")
            print("\nİçerik örneği:")
            print("[default]")
            print("aws_access_key_id = SIZIN_ACCESS_KEY_ID")
            print("aws_secret_access_key = SIZIN_SECRET_ACCESS_KEY")
            return False
        
        print(f"✓ Access Key ID: {credentials.access_key[:4]}...{credentials.access_key[-4:]}")
        
        # 2. STS ile kimlik doğrulama
        print("\n[2/3] AWS STS ile kimlik doğrulanıyor...")
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✓ Account ID: {identity['Account']}")
        print(f"✓ User ARN: {identity['Arn']}")
        print(f"✓ User ID: {identity['UserId']}")
        
        # 3. Region kontrolü
        print("\n[3/3] Region ayarı kontrol ediliyor...")
        region = session.region_name
        if region:
            print(f"✓ Aktif Region: {region}")
        else:
            print("⚠ Uyarı: Region ayarlanmamış, varsayılan 'us-east-1' kullanılacak")
            region = 'us-east-1'
        
        # Bonus: Mevcut RDS instance'larını listele
        print("\n[BONUS] Mevcut RDS instance'ları kontrol ediliyor...")
        try:
            rds = boto3.client('rds', region_name=region)
            response = rds.describe_db_instances()
            
            if response['DBInstances']:
                print(f"✓ {len(response['DBInstances'])} adet RDS instance bulundu:")
                for db in response['DBInstances']:
                    print(f"  - {db['DBInstanceIdentifier']} ({db['DBInstanceStatus']})")
            else:
                print("✓ Henüz RDS instance yok (yeni deployment için hazır)")
        except ClientError as e:
            if 'AccessDenied' in str(e):
                print("⚠ RDS listeleme yetkisi yok (deployment için gerekli)")
            else:
                print(f"⚠ RDS kontrolü başarısız: {e}")
        
        print("\n" + "=" * 60)
        print("✅ AWS BAĞLANTISI BAŞARILI!")
        print("=" * 60)
        print("\n📋 Deployment için gerekli yetkiler:")
        print("  • RDS (PostgreSQL database oluşturma)")
        print("  • ECR (Docker image registry)")
        print("  • ECS (Fargate container oluşturma)")
        print("  • EC2 (Security groups, Load Balancer)")
        print("  • IAM (Task execution roles)")
        print("  • CloudWatch (Logging ve monitoring)")
        print("\nYetkileri kontrol etmek için IAM console'u kullanın:")
        print("https://console.aws.amazon.com/iam/")
        
        return True
        
    except NoCredentialsError:
        print("\n✗ HATA: AWS kimlik bilgileri bulunamadı!")
        print("\nLütfen C:\\Users\\berat\\.aws\\credentials dosyasını oluşturun")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidClientTokenId':
            print("\n✗ HATA: Access Key ID geçersiz!")
        elif error_code == 'SignatureDoesNotMatch':
            print("\n✗ HATA: Secret Access Key yanlış!")
        else:
            print(f"\n✗ HATA: {e}")
        return False
        
    except Exception as e:
        print(f"\n✗ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_aws_connection()
    sys.exit(0 if success else 1)
